# vim: ts=4 et sw=4 sts=4
# -*- coding: utf-8 -*-
import asyncio
import irc3
from irc3.plugins.command import command
from irc3.utils import IrcString
import time
import threading
import os
import shutil
import ZODB
import ZODB.FileStorage

from decorators import nickserv_identified
from modules import chatbase, eventbase
from modules.timer import SpamProtect
from modules.effectbase import EffectBase
from modules.gamebase import Gamebase
from modules.itembase import ItemBase
from modules.callbackqueue import CallbackQueue, CallbackQueueWorkerThread
from modules.types import *
from modules.utils import get_logger, level_to_points, try_fun, set_msg_fun
from modules.markov import Markov

logger = get_logger('main')

ADMINS = []  # only required until commands are available to the public
MAIN_CHANNEL = '#aeolus'

NICKSERV_WAIT_TICKS = 200
NICKSERVIDENTIFIEDRESPONSES = {}
NICKSERVRESPONSESLOCK = None


@irc3.extend
def action(bot, *args, nowait=False):
    bot.privmsg(args[0], '\x01ACTION ' + args[1] + '\x01', nowait=nowait)


def player_id(mask):
    assert type(mask) == irc3.utils.IrcString
    n = mask.host.split('@', 1)[0]
    try:
        # if it's a number, return it the way it's presented - as string, since sorting int/str in one dict doesn't work
        int(n)
        return n
    except Exception:
        # for irc accounts
        return mask.nick


@irc3.plugin
class Plugin(object):

    requires = [
        'irc3.plugins.userlist',
    ]

    def __init__(self, bot):
        # TODO run connection.cacheMinimize() every once in a while
        self.bot = bot
        self.loop = asyncio.new_event_loop()
        storage = ZODB.FileStorage.FileStorage(self.bot.config['chat_db'])
        self.db = ZODB.DB(storage)
        self.db_con = self.db.open()
        self.db_root = self.db_con.root
        set_msg_fun(ChatType.IRC, self.irc_message)

        # every manager/base added here should be able to be reset
        # soooo turns out sometimes they seem to lose ref to each other and get a new object? requires the set methods
        try:
            self.db_root.queue.print()
        except:
            self.db_root.queue = CallbackQueue()
        self.db_root.queue.migrate()
        self.queue_thread = CallbackQueueWorkerThread(self.db_root.queue)
        self.queue_thread.start()

        try:
            self.db_root.effectbase.set(self.db_root.queue)
            self.db_root.effectbase.print()
        except:
            self.db_root.effectbase = EffectBase(self.db_root.queue)
        self.db_root.effectbase.migrate()

        itembase_args = [self.db_root.queue, self.db_root.effectbase]
        try:
            self.db_root.itembase.set(*itembase_args)
            self.db_root.itembase.print()
        except:
            self.db_root.itembase = ItemBase(*itembase_args)
        self.db_root.itembase.migrate()

        try:
            self.db_root.spam_protect.print()
        except:
            self.db_root.spam_protect = SpamProtect()
        self.db_root.spam_protect.migrate()

        try:
            self.db_root.eventbase.print()
        except:
            self.db_root.eventbase = eventbase.Eventbase()
        self.db_root.eventbase.migrate()

        chatbase_args = [self.db_root.eventbase, self.db_root.spam_protect, self.db_root.queue, self.db_root.effectbase,
                         self.db_root.itembase]
        try:
            self.db_root.chatbase.set(*chatbase_args)
            self.db_root.chatbase.print()
        except:
            self.db_root.chatbase = chatbase.Chatbase(*chatbase_args)
        self.db_root.chatbase.migrate()

        gamebase_args = [self.db_root.eventbase, self.db_root.queue, self.db_root.chatbase,
                         self.db_root.effectbase, self.db_root.spam_protect]
        try:
            self.db_root.gamebase.set(*gamebase_args)
            self.db_root.gamebase.print()
        except:
            self.db_root.gamebase = Gamebase(*gamebase_args)
        self.db_root.gamebase.migrate()

        # markov chain generators
        self.markov_aeolus = Markov(self, self.bot.config.get('markov_aeolus', './data/misc/aeolus.json'))

    @classmethod
    def reload(cls, old):
        return cls(old.bot)

    @irc3.event(irc3.rfc.CONNECTED)
    def nickserv_auth(self, *args, **kwargs):
        self.bot.privmsg('nickserv', 'identify %s' % self.bot.config['nickserv_password'])
        self.on_restart()

    @irc3.event(irc3.rfc.JOIN)
    def on_join(self, channel, mask):
        self.db_root.chatbase.on_join(ChatType.IRC, player_id(mask), mask.nick, channel_id=channel)

    @irc3.event(irc3.rfc.PRIVMSG)
    async def on_privmsg(self, *args, **kwargs):
        msg, channel, sender = kwargs['data'], kwargs['target'], kwargs['mask']
        if self.bot.config['nick'] in sender.nick:
            return
        if sender.startswith("NickServ!"):
            self.__handle_nickserv_message(msg)
            return
        self.db_root.chatbase.on_chat(msg, player_id(sender), sender.nick, channel_id=channel)

    @irc3.event(irc3.rfc.KICK)
    async def on_kick(self, *args, **kwargs):
        by, target = kwargs.get('mask').nick, kwargs['target']
        channel, reason = kwargs.get('channel', '?'), kwargs.get('data', '?')
        self.db_root.chatbase.on_kick(by, target, channel, reason)

    @irc3.event(irc3.rfc.MODE)
    async def on_mode(self, *args, **kwargs):
        logger.info('MODE: %s %s' % (str(args), str(kwargs)))
        """
        MODE  () {'modes': '+b', 'target': '#shadows', 'event': 'MODE', 'mask': 'Washy!Washy@whatever', 'data': '*!*@<ip/provider>'}
        -b
        """
        pass

    @staticmethod
    def _is_a_channel(channel):
        return IrcString(channel).is_channel

    def __is_in_bot_channel(self, player):
        for channel in self.bot.channels:
            if self.__is_in_channel(player, self.bot.channels[channel]):
                return True, channel
        return False, None

    @staticmethod
    def __is_in_channel(player, channel):
        if player in channel:
            return True
        return False

    async def __is_nick_serv_identified(self, nick):
        self.bot.privmsg('nickserv', "status {}".format(nick))
        global NICKSERV_WAIT_TICKS
        remaining_tries = NICKSERV_WAIT_TICKS + 0
        while remaining_tries > 0:
            if NICKSERVIDENTIFIEDRESPONSES.get(nick):
                value = NICKSERVIDENTIFIEDRESPONSES[nick]
                NICKSERVRESPONSESLOCK.acquire()
                del NICKSERVIDENTIFIEDRESPONSES[nick]
                NICKSERVRESPONSESLOCK.release()
                if int(value) == 3:
                    return True
                return False
            remaining_tries -= 1
            await asyncio.sleep(0.1)
        return False

    def __handle_nickserv_message(self, message):
        message = " ".join(message.split())
        NICKSERVRESPONSESLOCK.acquire()
        if message.startswith('STATUS'):
            words = message.split(" ")
            NICKSERVIDENTIFIEDRESPONSES[words[1]] = words[2]
        NICKSERVRESPONSESLOCK.release()

    def on_restart(self):
        t0 = time.clock()

        # TODO get rid of global vars
        global NICKSERVRESPONSESLOCK, ADMINS
        NICKSERVRESPONSESLOCK = threading.Lock()

        # default vars for cooldowns, some costs, requirements  # TODO make command to modify
        for k, v in {
            'points_cost_on_kick': -500,                                    # for chatbase
            'points_cost_on_ban': -1000,                                    # for chatbase
            'default_cd': self.bot.config.get('spam_protect_time', 600),    # for spamprotect
        }.items():
            self.__db_add(['vars'], k, v, overwrite_if_exists=False, save=False)
        # for t in ['chattip', 'chatlvl', 'chatladder']:
        #     self.__db_add(['timers'], t, default_cd, overwrite_if_exists=False, save=False)

        # forcefully add some silent bots to the entity list, so events etc register correctly
        for n in ['AeonCommander', 'CybranCommander', 'UefCommander', 'SeraCommander', self.bot.config['nick']]:
            self.db_root.chatbase.add(n, n)

        # add misc other defaults/paths to db.json
        self.__db_add(['chatlvlmisc'], 'epoch', 1, overwrite_if_exists=False, save=True)

        level_to_points(500)  # cache levels up to 500

        # get misc vars from db.json
        ADMINS = [n.split('@')[0].replace('!', '').replace('*', '')
                  for n, v in self.bot.config['irc3.plugins.command.masks'].items() if len(v) > 5]

        # update stuff
        self.db_root.effectbase.update_effects_list(self.bot.config['effects_file'])
        self.db_root.itembase.update_items_list(self.bot.config['items_file'])
        self.db_root.spam_protect.update_timer(self.__db_get(['timers']))
        vars_ = self.__db_get(['vars'])
        self.db_root.chatbase.update_vars(**vars_)
        self.db_root.eventbase.update_vars(**vars_)
        self.db_root.gamebase.update_vars(**vars_)
        self.db_root.spam_protect.update_vars(**vars_)

        logger.info('Admins: %s' % str(ADMINS))
        logger.info("Startup time: {t}".format(**{"t": format(time.clock() - t0, '.4f')}))

    def pm(self, mask, target, message, action_=False, nowait=True):
        """ Fixes bot PMing itself instead of the user if privmsg is called by user in PM instead of a channel. """
        if target == self.bot.config['nick']:
            if isinstance(mask, IrcString):
                target = mask.nick
            else:
                target = mask
        fun = self.bot.action if action_ else self.bot.privmsg
        return fun(target, message, nowait=nowait)

    def irc_message(self, target, message, action_=False):
        """ Used via utils by some other modules """
        fun = self.bot.action if action_ else self.bot.privmsg
        try:
            fun(target, message, nowait=True)
            return
        except AttributeError as e1:
            try:
                fun(target, message, nowait=False)
                return
            except Exception as e2:
                logger.warning('Failed sending IRC message! [%s] [%s]' % (str(e1), str(e2)))

    def is_in_channel(self, player, channel):
        if isinstance(channel, str):
            channel = self.bot.channels[channel]
        if player in channel:
            return True
        return False

    @command(permission='admin', show_in_help_list=False)
    @nickserv_identified
    async def join(self, mask, target, args):
        """ Join the given channel

            %%join <channel>
        """
        logger.debug('%d, cmd %s, %s, %s' % (time.time(), 'join', mask.nick, target))
        self.bot.join(args['<channel>'])
        self.db_root.eventbase.add_command_event(CommandType.JOIN, by_=player_id(mask), target=target, args=args)

    @command(permission='admin', show_in_help_list=False)
    @nickserv_identified
    async def leave(self, mask, target, args):
        """ Leave the given channel

            %%leave
            %%leave <channel>
        """
        logger.debug('%d, cmd %s, %s, %s' % (time.time(), 'leave', mask.nick, target))
        channel = args['<channel>']
        if channel is None:
            channel = target
        self.bot.part(channel)
        self.db_root.eventbase.add_command_event(CommandType.LEAVE, by_=player_id(mask), target=target, args=args)

    def spam_protect_wrap(self, channel, cmd, mask, cmd_type, target, args):
        """ just spam_protect with informing user of remaining time and logging the event """
        is_spam, rem_time = self.db_root.spam_protect.is_spam(channel, cmd)
        if is_spam:
            self.pm(mask, mask.nick, 'The command group "%s" is on cooldown, please wait %d seconds.' % (cmd, rem_time))
            self.db_root.eventbase.add_command_event(cmd_type, by_=player_id(mask), target=target,
                                                     args=args, spam_protect_time=rem_time)
        return is_spam

    @command()
    async def chain(self, mask, target, args):
        """ Chain words both directions <3\n
            <type> is in {f, b} to make the chain unidirectional

            %%chain <word>
            %%chain <word> f
            %%chain <word> b
        """
        # TODO remove when public
        if mask.nick not in ADMINS:
            return
        if self.spam_protect_wrap(target, 'chain', mask, CommandType.CHAIN, target, args):
            return
        word, forward, backward, sentence = args.get('<word>'), args.get('f'), args.get('b'), ''
        if not forward and not backward:
            forward = backward = True
        if backward:
            sentence += self.markov_aeolus.sentence(word, target, include_word=True, forward=False) + ' '
        if forward:
            sentence += self.markov_aeolus.sentence(word, target, include_word=not backward, forward=True)
        self.bot.privmsg(target, sentence)

    @command()
    async def chainprob(self, mask, target, args):
        """ Retrieve the probability of words in order

            %%chainprob <word1> [<word2>]
        """
        # TODO remove when public
        if mask.nick not in ADMINS:
            return
        if self.spam_protect_wrap(target, 'chainprob', mask, CommandType.CHAINPROB, target, args):
            return
        w1, w2 = args.get('<word1>'), args.get('<word2>')
        self.bot.privmsg(target, self.markov_aeolus.chainprob(w1, w2))

    @command()
    async def chatlvl(self, mask, target, args):
        """ Display chatlvl + points

            %%chatlvl [<name>]
        """
        logger.debug('%d, cmd %s, %s, %s' % (time.time(), 'chatlvl', mask.nick, target))
        # TODO remove when public
        if mask.nick not in ADMINS:
            return
        name = args.get('<name>')
        name = mask.nick if name is None else name
        is_spam, rem_time = self.db_root.spam_protect.is_spam(target, 'chatlvl')
        location = mask.nick if is_spam else target
        self.pm(mask, location, self.db_root.chatbase.get(name, is_nick=True).get_point_message())
        self.db_root.eventbase.add_command_event(CommandType.CHATLVL, by_=player_id(mask), target=target, args=args,
                                                 spam_protect_time=rem_time)

    @command()
    async def chateffects(self, mask, target, args):
        """ Display effects and mults

            %%chateffects [<name>]
        """
        logger.debug('%d, cmd %s, %s, %s' % (time.time(), 'chatlvl', mask.nick, target))
        # TODO remove when public
        if mask.nick not in ADMINS:
            return
        name = args.get('<name>')
        name = mask.nick if name is None else name
        is_spam, rem_time = self.db_root.spam_protect.is_spam(target, 'chateffects')
        location = mask.nick if is_spam else target
        msg = self.db_root.chatbase.get(name, is_nick=True).get_effects_message()
        for i, m in enumerate(msg.split('\n')):
            self.pm(mask, location, m)
        self.db_root.eventbase.add_command_event(CommandType.CHATEFFECTS, by_=player_id(mask), target=target, args=args,
                                                 spam_protect_time=rem_time)

    @command()
    async def chatitems(self, mask, target, args):
        """ Display items of user

            %%chatitems [<name>]
        """
        logger.debug('%d, cmd %s, %s, %s' % (time.time(), 'chatitems', mask.nick, target))
        # TODO remove when public
        if mask.nick not in ADMINS:
            return
        name = args.get('<name>')
        name = mask.nick if name is None else name
        is_spam, rem_time = self.db_root.spam_protect.is_spam(target, 'chatitems')
        location = mask.nick if is_spam else target
        pid = player_id(mask)
        msg = self.db_root.chatbase.get(name, is_nick=True).get_usable_items_message()
        for i, m in enumerate(msg.split('\n')):
            self.pm(mask, location, m)
        self.db_root.eventbase.add_command_event(CommandType.CHATITEMS, by_=pid, target=target, args=args,
                                                 spam_protect_time=rem_time)

    @command()
    async def useitem(self, mask, target, args):
        """ Display items of user

            %%useitem <item_name> [<user_name>]
        """
        logger.debug('%d, cmd %s, %s, %s' % (time.time(), 'chatitems', mask.nick, target))
        # TODO remove when public
        if mask.nick not in ADMINS:
            return
        item_name, user_name = args.get('<item_name>'), args.get('<user_name>')
        user_name = mask.nick if user_name is None else user_name
        is_spam, rem_time = self.db_root.spam_protect.is_spam(target, 'useitem')
        location = mask.nick if is_spam else target
        pid = player_id(mask)
        msg = self.db_root.chatbase.use_item(item_name, pid, user_name, is_item_name=True, is_target_nick=True)
        for i, m in enumerate(msg.split('\n')):
            self.pm(mask, location, m)
        self.db_root.eventbase.add_command_event(CommandType.USEITEM, by_=pid, target=target, args=args,
                                                 spam_protect_time=rem_time)

    @command()
    async def chatladder(self, mask, target, args):
        """ The names of the top ladder warriors

            %%chatladder
            %%chatladder all
            %%chatladder <sum/type> [rev]
        """
        # TODO remove when public
        if mask.nick not in ADMINS:
            return
        logger.debug('%d, cmd %s, %s, %s' % (time.time(), 'chatladder', mask.nick, target))
        if self.spam_protect_wrap(target, 'chatladder', mask, CommandType.CHATLADDER, target, args):
            return
        rev, all_ = args.get('rev'), args.get('all')
        point_type = PointType.from_str(args.get('<sum/type>'))
        msg = self.db_root.chatbase.get_k_points_str(largest=not rev, incl_channels=all_, point_type=point_type)
        self.pm(mask, target, 'The ranking! %s' % msg)
        self.db_root.eventbase.add_command_event(CommandType.CHATLADDER, by_=player_id(mask), target=target, args=args)

    @command()
    async def chatevents(self, mask, target, args):
        """ Find (recent) logged events,
            Use . to mark unnecessary filters

            %%chatevents <type> <nick> <time>
            %%chatevents command <type> <nick> <time>
        """
        # TODO remove when public
        if mask.nick not in ADMINS:
            return
        logger.debug('%d, cmd %s, %s, %s' % (time.time(), 'chatevents', mask.nick, target))
        if self.spam_protect_wrap(target, 'chatevents', mask, CommandType.CHATEVENTS, target, args):
            return
        etype_, nick_, time_ = args.get('<type>'), args.get('<nick>'), args.get('<time>')
        time_ = try_fun(int, None, time_)
        id_ = self.db_root.chatbase.get_id(nick_)
        msg = self.db_root.eventbase.recent_events_str(etype_, id_, nick_, time_, command_events=args.get('command'))
        self.db_root.eventbase.add_command_event(CommandType.CHATEVENTS, by_=player_id(mask), target=target, args=args)
        self.pm(mask, target, msg)

    @command()
    @nickserv_identified
    async def chattip(self, mask, target, args):
        """ Tip points to others <3

            %%chattip <name> [<amount>]
        """
        # TODO remove when public
        if mask.nick not in ADMINS:
            return
        logger.debug('%d, cmd %s, %s, %s' % (time.time(), 'chattip', mask.nick, target))
        if self.spam_protect_wrap(target, 'chattip', mask, CommandType.CHATTIP, target, args):
            return
        name, amount = args.get('<name>'), args.get('<amount>')
        amount = try_fun(int, None, amount) if amount is not None else 100
        if amount is None or amount <= 0:
            self.pm(mask, target, 'Failed tipping! Something is wrong with the amount.')
            return
        _, msg = self.db_root.chatbase.tip(mask.nick, name, amount, partial=True)
        self.db_root.eventbase.add_command_event(CommandType.CHATTIP, by_=player_id(mask), target=target, args=args)
        self.pm(mask, target, msg)

    @command
    @asyncio.coroutine
    def cr(self, mask, target, args):
        """ Shortcut to the chatroulette command

            %%cr <points/all>
        """
        yield from self.chatroulette(mask, target, args)

    @command
    @asyncio.coroutine
    def chatroulette(self, mask, target, args):
        """ Play the chat point roulette! Bet points, 20s after the initial roll, a winner is chosen.
            Probability scales with points bet. The winner gets all points.

            %%chatroulette <points/all>
        """
        # TODO remove when public
        if mask.nick not in ADMINS:
            return
        logger.debug('%d, cmd %s, %s, %s' % (time.time(), 'chatroulette', mask.nick, target))
        points = args.get('<points/all>')
        id_ = player_id(mask)
        if points == 'all':
            points = self.db_root.chatbase.get(id_).get_points()
        else:
            points = try_fun(int, None, points)
        if points is None:
            self.pm(mask, target, 'Failed understanding your point amount!')
        try:
            game = self.db_root.gamebase.get_roulette_game(ChatType.IRC, target, id_)
            if game is not None:
                game.join(id_, mask.nick, points)
        except Exception as e:
            self.pm(mask, target, str(e))
        self.db_root.eventbase.add_command_event(CommandType.CHATROULETTE, by_=player_id(mask),
                                                 target=target, args=args)

    @command(show_in_help_list=False)
    async def test(self, mask, target, args):
        """ Just testing stuff

            %%test [<name>]
        """
        if mask.nick not in ADMINS:
            return
        logger.debug('%d, cmd %s, %s, %s' % (time.time(), 'test', mask.nick, target))
        name = args.get('<name>')
        name = mask.nick if name is None else name
        id_ = self.db_root.chatbase.get_id(name)
        self.db_root.chatbase.add_test_item(id_)
        self.pm(mask, target, 'Adding test item to %s:%s' % (name, id_))

    @command(permission='admin', show_in_help_list=False)
    @nickserv_identified
    async def cd(self, mask, target, args):
        """ Set cooldowns

            %%cd get
            %%cd get <timer>
            %%cd set <timer> <time>
        """
        logger.debug('%d, cmd %s, %s, %s' % (time.time(), 'cd', mask.nick, target))
        get, set_, timer, time_ = args.get('get'), args.get('set'), args.get('<timer>'), args.get('<time>')
        timers, default_cd = self.db_root.spam_protect.timer, self.db_root.spam_protect.default_cd
        if get:
            if timer:
                self.pm(mask, mask.nick, 'The cooldown for "%s" is set to %i' % (timer, timers.get(timer, default_cd)))
            else:
                for key in timers.keys():
                    self.pm(mask, mask.nick, 'The cooldown for "%s" is set to %i' % (key, timers.get(key, default_cd)))
        if set_:
            timers[timer] = int(time_)
            self.db_root.spam_protect.update_timer(timers)
            self.__db_add(['timers'], timer, timers[timer], save=True)
            self.pm(mask, target, 'The cooldown for %s is now changed to %i' % (timer, timers[timer]))
        self.db_root.eventbase.add_command_event(CommandType.CD, by_=player_id(mask), target=target, args=args)

    @command(permission='admin', public=False)
    @nickserv_identified
    async def reload(self, mask, target, args):
        """ Reload bot components

            %%reload effects
        """
        logger.debug('%d, cmd %s, %s, %s' % (time.time(), 'reload', mask.nick, target))
        if args.get('effects'):
            self.db_root.effectbase.update_effects_list(self.bot.config['effects_file'])
            self.db_root.itembase.update_items_list(self.bot.config['items_file'])
        self.db_root.eventbase.add_command_event(CommandType.RELOAD, by_=player_id(mask), target=target, args=args)

    def backup(self, name='backup', keep=3):
        data_path = '/'.join(self.bot.config.get('chat_db', './data/chat/data.fs').split('/')[:-1])
        backup_dir = '%s%s/' % (self.bot.config.get('backups_path', './backups/'), name)
        backup_path = '%s%s/' % (backup_dir, str(int(time.time())))
        logger.info('Backup from "%s" to "%s"' % (data_path, backup_path))
        self.__db_save()
        shutil.copytree(data_path, backup_path, ignore=lambda _, names: [n for n in names if n.endswith('.lock')])
        all_relevant_backups = [d[0] for d in os.walk(backup_dir)]
        for i in range(1, len(all_relevant_backups) - keep):
            shutil.rmtree(all_relevant_backups[i])

    @command(show_in_help_list=False)
    @nickserv_identified
    async def adminbackup(self, mask, target, args):
        """ Back up the db

            %%adminbackup
        """
        logger.info('%d, cmd %s, %s, %s' % (time.time(), 'adminbackup', mask.nick, target))
        self.backup('manually', keep=5)
        self.pm(mask, target, 'Backed up the db')
        self.db_root.eventbase.add_command_event(CommandType.ADMINBACKUP, by_=player_id(mask),
                                                 target=target, args=args)

    @command(permission='admin', public=False)
    @nickserv_identified
    async def admineffects(self, mask, target, args):
        """ Abuse admin powers to fiddle with effects

            %%admineffects add <name> <effectid>
        """
        logger.info('%d, cmd %s, %s, %s' % (time.time(), 'admineffects', mask.nick, target))
        name, effect_id = args.get('<name>'), args.get('<effectid>')
        msg = self.db_root.chatbase.apply_effect(name, effect_id, is_player_nick=True, is_effect_name=False)
        self.pm(mask, mask.nick, msg)
        self.db_root.eventbase.add_command_event(CommandType.ADMINEFFECTS, by_=player_id(mask),
                                                 target=target, args=args)

    @command(permission='admin', public=False)
    @nickserv_identified
    async def adminitems(self, mask, target, args):
        """ Abuse admin powers to fiddle with items

            %%adminitems add <name> <itemid>
        """
        logger.info('%d, cmd %s, %s, %s' % (time.time(), 'adminitems', mask.nick, target))
        name, item_id = args.get('<name>'), args.get('<itemid>')
        msg = self.db_root.chatbase.add_item(name, item_id, is_player_nick=True, is_item_name=False)
        self.pm(mask, mask.nick, msg)
        self.db_root.eventbase.add_command_event(CommandType.ADMINITEMS, by_=player_id(mask),
                                                 target=target, args=args)

    @command(permission='admin', public=False)
    @asyncio.coroutine
    def adminignore(self, mask, target, args):
        """ Change the ignore list

            %%adminignore get
            %%adminignore add <name> [<time>]
            %%adminignore del <name>
        """
        logger.info('%d, cmd %s, %s, %s' % (time.time(), 'adminignore', mask.nick, target))
        get, add, del_, name, response = args.get('get'), args.get('add'), args.get('del'), args.get('<name>'), None
        time_ = args.get('<time>')
        if get:
            response = self.db_root.chatbase.get_ignore_list()
        if add:
            time_ = try_fun(int, None, time_)
            response = self.db_root.chatbase.add_to_ignore(name, duration=time_)
        if del_:
            response = self.db_root.chatbase.remove_from_ignore(name)
        self.db_root.eventbase.add_command_event(CommandType.ADMINIGNORE, by_=player_id(mask),
                                                 target=target, args=args)
        self.pm(mask, mask.nick, response)

    @command(permission='admin', public=False)
    @asyncio.coroutine
    def adminchannels(self, mask, target, args):
        """ Change list of channels where one can get points for chatting;
            type in {chat, game, spam}

            %%adminchannels <type> get
            %%adminchannels <type> add <name> [<time>]
            %%adminchannels <type> del <name>
        """
        logger.info('%d, cmd %s, %s, %s' % (time.time(), 'adminchannels', mask.nick, target))
        get, add, del_, name, response = args.get('get'), args.get('add'), args.get('del'), args.get('<name>'), None
        type_, time_ = args.get('<type>'), args.get('<time>')
        funs = {'chat': {'get': self.db_root.chatbase.get_accepted_chat,
                         'add': self.db_root.chatbase.add_accepted_chat,
                         'del': self.db_root.chatbase.remove_accepted_chat},
                'game': {'get': self.db_root.chatbase.get_accepted_game,
                         'add': self.db_root.chatbase.add_accepted_game,
                         'del': self.db_root.chatbase.remove_accepted_game},
                'spam': {'get': self.db_root.spam_protect.get_protected_channel,
                         'add': self.db_root.spam_protect.add_protected_channel,
                         'del': self.db_root.spam_protect.remove_protected_channel},
                }.get(type_, None)
        if funs is None:
            self.pm(mask, mask.nick, 'Type "%s" not found!' % type_)
            return
        if get:
            response = funs.get('get')()
        if add:
            time_ = try_fun(int, None, time_)
            response = funs.get('add')(name, duration=time_)
        if del_:
            response = funs.get('del')(name)
        self.db_root.eventbase.add_command_event(CommandType.ADMINCHANNELS, by_=player_id(mask),
                                                 target=target, args=args)
        self.pm(mask, mask.nick, response)

    @command(permission='admin', public=False)
    @nickserv_identified
    async def adminreset(self, mask, target, args):
        """ Abuse admin powers to reset everything

            %%adminreset all
            %%adminreset chat
            %%adminreset games
            %%adminreset events
        """
        logger.info('%d, cmd %s, %s, %s' % (time.time(), 'adminreset', mask.nick, target))
        all_, games, events = args.get('all', False), args.get('games', False), args.get('events', False)
        chat = args.get('chat', False)
        self.db_root.eventbase.add_command_event(CommandType.ADMINRESET, by_=player_id(mask),
                                                 target=target, args=args)
        self.reset(name='manually_reset', all_=all_, games=games, events=events, chat=chat)
        self.pm(mask, mask.nick, "RESET STUFF")

    def reset(self, name='reset', all_=False, games=False, events=False, chat=False):
        epoch = self.__db_get(['chatlvlmisc', 'epoch'])
        self.__db_add(['chatlvlmisc'], 'epoch', epoch+1, overwrite_if_exists=True, save=True)
        logger.info('-'*100)
        self.backup(name)
        if all_:
            self.db_root.queue.reset()
            self.db_root.spam_protect.reset()
        if all_ or chat:
            self.db_root.chatbase.reset()
        if all_ or events:
            self.db_root.eventbase.reset()
        if all_ or games:
            self.db_root.gamebase.reset()
        self.on_restart()

    @command(permission='admin', public=False)
    async def hidden(self, mask, target, args):
        """ Actually shows hidden commands

            %%hidden
        """
        logger.debug('%d, cmd %s, %s, %s' % (time.time(), 'hidden', mask.nick, target))
        words = ["join", "leave", "cd", "reload", "adminbackup", "admineffects", "adminignore", "adminchannels",
                 "adminreset"]
        self.bot.privmsg(mask.nick, "Hidden commands (!help <command> for more info):")
        self.bot.privmsg(mask.nick, ", ".join(words))
        self.db_root.eventbase.add_command_event(CommandType.HIDDEN, by_=player_id(mask), target=target, args=args)

    def __db_add(self, path, key, value, overwrite_if_exists=True, try_saving_with_new_key=False, save=True):
        cur = self.bot.db
        for p in path:
            if p not in cur:
                cur[p] = {}
            cur = cur[p]
        exists, added_with_new_key = cur.get(key), False
        if overwrite_if_exists:
            cur[key] = value
        elif not exists:
            cur[key] = value
        elif exists and try_saving_with_new_key:
            for i in range(0, 1000):
                if not cur.get(key + str(i)):
                    cur[key + str(i)] = value
                    added_with_new_key = True
                    break
        if save:
            self.__db_save()
        return cur, exists, added_with_new_key

    def __db_del(self, path, key, save=True):
        cur = self.bot.db
        for p in path:
            cur = cur.get(p, {})
        if not cur.get(key) is None:
            del cur[key]
            if save:
                self.__db_save()
        return cur

    def __db_get(self, path):
        reply = self.bot.db
        for p in path:
            reply = reply.get(p, {})
        return reply

    def __db_save(self):
        self.bot.db.set('misc', lastSaved=time.time())
