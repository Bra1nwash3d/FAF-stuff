import random
import asyncio
import re
import itertools
import irc3
from irc3.plugins.command import command
import time
import threading

from taunts import USE_FORBIDDEN, TALKING_REACTION, TAUNTS
NICKSERVIDENTIFIEDRESPONSES = {}
NICKSERVIDENTIFIEDRESPONSESLOCK = None

CLANMEMBER = {}
IGNOREUSERS = ['NickServ', 'ChanServ', 'OperServ']
ALLTAUNTS = []
BEQUIETCHANNELS = ['#aeolus']
MODERATEDCHANNELS = []


@irc3.extend
def action(bot, *args):
    bot.privmsg(args[0], '\x01ACTION ' + args[1] + '\x01')

@irc3.plugin
class Plugin(object):

    def __init__(self, bot):
        self.bot = bot
        self.timers = {}
        self._rage = {}

        global ALLTAUNTS, IGNOREUSERS, MODERATEDCHANNELS, NICKSERVIDENTIFIEDRESPONSESLOCK
        NICKSERVIDENTIFIEDRESPONSESLOCK = threading.Lock()
        ALLTAUNTS.extend(USE_FORBIDDEN)
        ALLTAUNTS.extend(TAUNTS)
        ALLTAUNTS.extend(TALKING_REACTION)
        IGNOREUSERS.extend([self.bot.config['nick']])
        for channel in self.bot.config['moderatedChannels']:
            MODERATEDCHANNELS.append('#' + channel)

    @classmethod
    def reload(cls, old):
        return cls(old.bot)

    def after_reload(self):
        self._taunt('#qai_channel')

    @irc3.event(irc3.rfc.CONNECTED)
    def nickserv_auth(self, *args, **kwargs):
        self.bot.privmsg('nickserv', 'identify %s' % self.bot.config['nickserv_password'])
        if 'clan' in self.bot.db:
            if 'names' in self.bot.db['clan']:
                global CLANMEMBER
                CLANMEMBER = self.bot.db['clan'].get('names', {}) #doing this here to init CLANMEMBER after the bot got its db

    @irc3.event(irc3.rfc.JOIN)
    def on_join(self, channel, mask):
        pass

    def move_user(self, channel, nick):
        self.bot.privmsg('OperServ', 'svsjoin %s %s' % (nick, channel))

    @irc3.event(irc3.rfc.PRIVMSG)
    @asyncio.coroutine
    def on_privmsg(self, *args, **kwargs):
        msg, channel, sender = kwargs['data'], kwargs['target'], kwargs['mask']
        #print(sender + ": " + msg)
        print(sender.nick + ": " + msg)
        if sender.startswith("NickServ!"):
            self.__handleNickservMessage(msg)
        if sender.nick in IGNOREUSERS:
            return
        if not channel in MODERATEDCHANNELS:
            return

    @command
    @asyncio.coroutine
    def taunt(self, mask, target, args):
        """Send a taunt

            %%taunt
            %%taunt <person>
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        if self.__handledNonMember(mask.nick, target, USE_FORBIDDEN):
            return
        p = args.get('<person>')
        if p == self.bot.config['nick']:
            p = mask.nick
        self.__taunt(nick=p, channel=target, tauntTable=TAUNTS)

    @command(permission='admin')
    @asyncio.coroutine
    def join(self, mask, target, args):
        """Overtake the given channel

            %%join <channel>
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        self.bot.join(args['<channel>'])

    @command(permission='admin')
    @asyncio.coroutine
    def leave(self, mask, target, args):
        """Leave the given channel

            %%leave
            %%leave <channel>
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        channel = args['<channel>']
        if channel is None:
            channel = target
        self.bot.part(channel)

    @command(permission='admin', public=False)
    @asyncio.coroutine
    def puppet(self, mask, target, args):
        """Puppet

            %%puppet <target> WORDS ...
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        t = args.get('<target>')
        m = " ".join(args.get('WORDS'))
        self.bot.privmsg(t, m)

    @command(permission='admin')
    @asyncio.coroutine
    def slap(self, mask, target, args):
        """Slap this guy

            %%slap <guy>
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        self.bot.action(target, "slaps %s " % args['<guy>'])

    def __taunt(self, nick, channel=None, tauntTable=TAUNTS):
        if channel is None:
            channel = "#qai_channel"
        if channel in BEQUIETCHANNELS:
            return
        if tauntTable is None:
            tauntTable = ALLTAUNTS
        self.bot.privmsg(channel, random.choice(tauntTable).format(**{
                'name' : nick
            }))

    def __handleNickservMessage(self, message):
        if message.startswith('STATUS'):
            words = message.split(" ")
            global NICKSERVIDENTIFIEDRESPONSES, NICKSERVIDENTIFIEDRESPONSESLOCK
            NICKSERVIDENTIFIEDRESPONSESLOCK.acquire()
            NICKSERVIDENTIFIEDRESPONSES[words[1]] = words[2]
            NICKSERVIDENTIFIEDRESPONSESLOCK.release()

    @asyncio.coroutine
    def __isNickservIdentified(self, nick):
        self.bot.privmsg('nickserv', "status {}".format(nick))
        remainingTries = 20
        while remainingTries > 0:
            if NICKSERVIDENTIFIEDRESPONSES.get(nick):
                value = NICKSERVIDENTIFIEDRESPONSES[nick]
                NICKSERVIDENTIFIEDRESPONSESLOCK.acquire()
                del NICKSERVIDENTIFIEDRESPONSES[nick]
                NICKSERVIDENTIFIEDRESPONSESLOCK.release()
                if int(value) == 3:
                    return True
                return False
            remainingTries -= 1
            yield from asyncio.sleep(0.1)
        return False

    @command(permission='admin', public=False)
    def clan(self, mask, target, args):
        """Adds/removes a user to/from the clanlist 

            %%clan get
            %%clan add <name>
            %%clan del <name>
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        global CLANMEMBER
        if 'clan' not in self.bot.db:
            self.bot.db['clan'] = {'names': {}}
        add, delete, get, name = args.get('add'), args.get('del'), args.get('get'), args.get('<name>')
        if add:
            try:
                allUser = self.bot.db['clan'].get('names', {})
                allUser[name] = True
                self.bot.db.set('clan', names=allUser)
                CLANMEMBER = allUser
                return 'Added "{name}" to clan members'.format(**{
                        "name": name,
                    })
            except:
                return "Failed adding the user. What did you do?!"
        elif delete:
            allUser = self.bot.db['clan'].get('names', {})
            if allUser.get(name):
                del self.bot.db['clan']['names'][name]
                CLANMEMBER = self.bot.db['clan'].get('names', {})
                return 'Removed "{name}" from clan members'.format(**{
                        "name": name,
                    })
            else:
                return 'Name not found in the list.'
        elif get:
            self.bot.privmsg(mask.nick, str(len(CLANMEMBER)) + " members listed:")
            self.bot.privmsg(mask.nick, 'names: ' + ', '.join(CLANMEMBER.keys()))

    def __isClanMember(self, nick):
        return nick in CLANMEMBER

    def __handledNonMember(self, nick, channel=None, tauntTable=TALKING_REACTION, kick=True):
        if self.__isClanMember(nick):
            return False
        if not channel:
            channel = nick
        elif kick == True:
            self.__kickFromChannel(nick, channel)
        self.__taunt(nick, channel=channel, tauntTable=tauntTable)
        return True

    def __kickFromChannel(self, nick, channel):
        self.bot.privmsg("ChanServ", "kick {channel} {nick}".format(**{
                'channel': channel,
                'nick': nick,
            }))

    @command
    def kick(self, mask, target, args):
        """Kick someone from channel

            %%kick <person>
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        if self.__handledNonMember(mask.nick, target, USE_FORBIDDEN):
            return
        p = args.get('<person>')
        if self.__isClanMember(p):
            return
        if p == self.bot.config['nick']:
            p = mask.nick
        self.__kickFromChannel(p, target)








