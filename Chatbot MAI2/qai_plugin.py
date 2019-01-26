# vim: ts=4 et sw=4 sts=4
# -*- coding: utf-8 -*-
import asyncio
import irc3
from irc3.plugins.command import command
from irc3.utils import IrcString
import time
import threading
import ZODB
import ZODB.FileStorage

from decorators import nickserv_identified, channel_only
from modules import chatbase, get_logger, eventbase
from modules.timer import SpamProtect
from modules.types import PointType, CommandType, EventType
from modules.utils import *

logger = get_logger.get_logger('main')

ADMINS = []
MAIN_CHANNEL = '#aeolus'
VARS = {}
DEFAULTVALUE = 500

NICKSERV_WAIT_TICKS = 60
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
        self.bot = bot
        self.loop = asyncio.new_event_loop()
        storage = ZODB.FileStorage.FileStorage(self.bot.config['storage2'])
        self.db = ZODB.DB(storage)
        self.db_con = self.db.open()
        self.db_root = self.db_con.root
        try:
            self.db_root.spam_protect.print()
        except:
            self.db_root.spam_protect = SpamProtect([MAIN_CHANNEL])
        try:
            self.db_root.eventbase.print()
        except:
            self.db_root.eventbase = eventbase.Eventbase()
        try:
            self.db_root.chatbase.print()
        except:
            self.db_root.chatbase = chatbase.Chatbase(self.db_root.eventbase, self.db_root.spam_protect)
        # TODO run connection.cacheMinimize() every once in a while
        level_to_points(500)  # cache levels up to 500
        global NICKSERVRESPONSESLOCK
        NICKSERVRESPONSESLOCK = threading.Lock()

    @classmethod
    def reload(cls, old):
        return cls(old.bot)

    @irc3.event(irc3.rfc.CONNECTED)
    def nickserv_auth(self, *args, **kwargs):
        self.bot.privmsg('nickserv', 'identify %s' % self.bot.config['nickserv_password'])
        self.on_restart()

    @irc3.event(irc3.rfc.JOIN)
    def on_join(self, channel, mask):
        if mask.nick == self.bot.config['nick']:
            return

    @irc3.event(irc3.rfc.PRIVMSG)
    async def on_privmsg(self, *args, **kwargs):
        msg, channel, sender = kwargs['data'], kwargs['target'], kwargs['mask']
        if self.bot.config['nick'] in sender.nick:
            return
        if sender.startswith("NickServ!"):
            self.__handle_nickserv_message(msg)
            return
        nick, id_ = sender.nick, player_id(sender)
        self.on_chat_msg('irc', msg, channel, nick, id_)

    def on_chat_msg(self, medium, msg, channel, nick, id_):
        self.db_root.chatbase.on_chat(msg, id_, nick, channel_id=channel)

    @irc3.event(irc3.rfc.KICK)
    async def on_kick(self, *args, **kwargs):
        kicktarget = kwargs['target']
        logger.info('{kicktarget} got kicked from {channel} by {nick} with reason "{reason}"!'.format(**{
            'kicktarget': kicktarget,
            'channel': kwargs.get('channel', '?'),
            'nick': kwargs.get('mask').nick,
            'reason': kwargs.get('data', '?'),
        }))

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
        time.clock()
        t0 = time.clock()
        global VARS, IGNOREDUSERS, ADMINS, DEFAULTVALUE
        ADMINS = [n.split('@')[0].replace('!', '').replace('*', '')
                  for n, v in self.bot.config['irc3.plugins.command.masks'].items() if len(v) > 5]
        default_cd = self.bot.config.get('spam_protect_time', 600)
        IGNOREDUSERS = self.__db_get(['ignoredusers'])
        VARS = self.__db_get(['vars'])
        self.__db_add([], 'ignoredusers', {}, overwrite_if_exists=False, save=False)
        for t in ['chattip', 'chatlvl', 'chatladder']:
            self.__db_add(['timers'], t, default_cd, overwrite_if_exists=False, save=False)
        for t in []:
            self.__db_add(['vars'], t, DEFAULTVALUE, overwrite_if_exists=False, save=False)
        self.__db_add([], 'chatlvlwords', {}, overwrite_if_exists=False, save=False)
        self.__db_add(['chatlvlmisc'], 'epoch', 1, overwrite_if_exists=False, save=True)
        self.db_root.spam_protect.update_timer(self.__db_get(['timers']), default_cd=default_cd)
        t1 = time.clock()
        logger.info('Admins: %s' % str(ADMINS))
        logger.info("Startup time: {t}".format(**{"t": format(t1 - t0, '.4f')}))

    def pm(self, mask, target, message, action_=False, nowait=True):
        """Fixes bot PMing itself instead of the user if privmsg is called by user in PM instead of a channel."""
        if target == self.bot.config['nick']:
            if isinstance(mask, IrcString):
                target = mask.nick
            else:
                target = mask
        fun = self.bot.action if action_ else self.bot.privmsg
        return fun(target, message, nowait=nowait)

    @command(permission='admin', show_in_help_list=False)
    @nickserv_identified
    async def join(self, mask, target, args):
        """Overtake the given channel

            %%join <channel>
        """
        logger.debug('%d, cmd %s, %s, %s' % (time.time(), 'join', mask.nick, target))
        self.bot.join(args['<channel>'])
        self.db_root.eventbase.add_command_event(CommandType.JOIN, by_=player_id(mask), target=target, args=args)

    @command(permission='admin', show_in_help_list=False)
    @nickserv_identified
    async def leave(self, mask, target, args):
        """Leave the given channel

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
    async def chatlvl(self, mask, target, args):
        """ Display chatlvl + points

            %%chatlvl [<name>]
        """
        logger.debug('%d, cmd %s, %s, %s' % (time.time(), 'chatlvl', mask.nick, target))
        location = target
        # TODO remove when public
        if mask.nick not in ADMINS:
            return
        name = args.get('<name>')
        name = mask.nick if name is None else name
        is_spam, rem_time = self.db_root.spam_protect.is_spam(location, 'chatlvl')
        if location == MAIN_CHANNEL and is_spam:
            location = mask.nick
        self.pm(mask, location, self.db_root.chatbase.get(name, is_nick=True).get_point_message())
        self.db_root.eventbase.add_command_event(CommandType.CHATLVL, by_=player_id(mask), target=target, args=args,
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
        # TODO update top chat guys i guess
        # global CHATLVLS, CHATLVL_TOPPLAYERS
        msg = self.db_root.chatbase.get_k_points_str(largest=not rev, incl_channels=all_, point_type=point_type)
        self.pm(mask, target, 'The ranking! %s' % msg)
        self.db_root.eventbase.add_command_event(CommandType.CHATLADDER, by_=player_id(mask), target=target, args=args)

    @command()
    async def chatevents(self, mask, target, args):
        """ Find (recent) logged events
            Use . to mark unnecessary filters

            %%chatevents <type> <nick> <time>
            %%chatevents command <type> <nick> <time>
        """
        # TODO add events (moderation: kick, ban / slaps)
        # TODO write sum+avg wait time
        # TODO remove when public
        if mask.nick not in ADMINS:
            return
        logger.debug('%d, cmd %s, %s, %s' % (time.time(), 'chatevents', mask.nick, target))
        if self.spam_protect_wrap(target, 'chatevents', mask, CommandType.CHATEVENTS, target, args):
            return
        is_command = args.get('command')
        etype_, nick_, time_ = args.get('<type>'), args.get('<nick>'), args.get('<time>')
        time_ = try_fun(int, None, time_)
        id_ = self.db_root.chatbase.get_id(nick_)
        events = self.db_root.eventbase.filter_time(t0d=time_)
        events = self.db_root.eventbase.filter_by(id_, events=events)
        misc_str = ''
        if is_command:
            # filter for command-events of command-type...
            type_ = CommandType.from_str(etype_)
            events = self.db_root.eventbase.filter_type([EventType.COMMAND], events=events)
            if type_ is not None:
                events = self.db_root.eventbase.filter_events(events, lambda e: e.command_type == type_)
            spam_sum = sum([e.get_spam_protect_time() for e in events])
            if len(events) > 0 and spam_sum > 0:
                misc_str += ', with an average spam protect time of %.1fs' % (spam_sum / len(events))
        else:
            # filter for events of event-type...
            type_ = EventType.from_str(etype_)
            events = self.db_root.eventbase.filter_type([type_], events=events)
        self.db_root.eventbase.add_command_event(CommandType.CHATEVENTS, by_=player_id(mask), target=target, args=args)
        self.pm(mask, target, '{n} {ty}events{tp} were logged{user}{time}{misc}'.format(**{
            'n': len(events),
            'ty': '' if not is_command else 'command-',
            'tp': '' if type_ is None else ' for type "%s"' % etype_,
            'user': '' if id_ is None else ' for %s' % nick_,
            'time': '' if time_ is None else ' in the past %d seconds' % time_,
            'misc': misc_str,
        }))

    @command()
    async def chattip(self, mask, target, args):
        """ Tip points to others <3

            %%chattip <name> [<amount>]
        """
        # TODO remove when public
        if mask.nick not in ADMINS:
            return
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
    async def hidden(self, mask, target, args):
        """Actually shows hidden commands
            %%hidden
        """
        logger.debug('%d, cmd %s, %s, %s' % (time.time(), 'hidden', mask.nick, target))
        words = ["join", "leave", "cd"]
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