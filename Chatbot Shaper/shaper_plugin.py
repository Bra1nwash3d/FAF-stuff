# vim: ts=4 et sw=4 sts=4
# -*- coding: utf-8 -*-
import numpy as np
import asyncio
import irc3
from irc3.plugins.command import command
import time
import threading

NICKSERVIDENTIFIEDRESPONSES = {}
NICKSERVIDENTIFIEDRESPONSESLOCK = None


@irc3.extend
def action(bot, *args):
    bot.privmsg(args[0], '\x01ACTION ' + args[1] + '\x01')

@irc3.plugin
class Plugin(object):

    requires = [
        'irc3.plugins.userlist'
    ]

    def __init__(self, bot):
        self.bot = bot
        self.timers = {}
        self._rage = {}
        global NICKSERVIDENTIFIEDRESPONSESLOCK
        NICKSERVIDENTIFIEDRESPONSESLOCK = threading.Lock()

    @classmethod
    def reload(cls, old):
        return cls(old.bot)

    def after_reload(self):
        pass

    @irc3.event(irc3.rfc.CONNECTED)
    def nickserv_auth(self, *args, **kwargs):
        self.bot.privmsg('nickserv', 'identify %s' % self.bot.config['nickserv_password'])

    @irc3.event(irc3.rfc.JOIN)
    def on_join(self, channel, mask):
        pass

    @irc3.event(irc3.rfc.PRIVMSG)
    @asyncio.coroutine
    def on_privmsg(self, *args, **kwargs):
        msg, channel, sender = kwargs['data'], kwargs['target'], kwargs['mask']
        if self.bot.config['nick'] in sender.nick:
            return

        if sender.startswith("NickServ!"):
            self.__handleNickservMessage(msg)

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

    @command(permission='admin', public=False)
    @asyncio.coroutine
    def design(self, mask, target, args):
        """Creates a new map list

            %%design add <listname> <ownername>
            %%design del <listname>
        """
        listname, ownername, add, delete = args.get('<listname>'), args.get('<ownername>'), args.get('add'), args.get('del')
        list, exists = self.__getList(listname)
        if add:
            if exists:
                self.__dbAdd(['maplists', listname], 'owner', ownername)
                return "This realm already exists, and I will not destroy it needlessly. Yet i have transferred ownership to the new ruler " + ownername + "."
            else:
                self.__dbAdd(['maplists'], listname, {'owner' : ownername,
                                                      'admins' : {},
                                                      'maps' : {}})
                return "I have done as you wished. The realm is created, and is given to " + ownername + "."
        if delete:
            if not exists:
                return "I can not delete what is not there."
            self.__dbDel(['maplists'], listname)
            return "As you wished, the realm was destroyed."

    def spam_protect(self, cmd, mask, target, args, specialSpamProtect=None):
        if not cmd in self.timers:
            self.timers[cmd] = {}
        if not target in self.timers[cmd]:
            self.timers[cmd][target] = 0
        spamProtectTimer = specialSpamProtect or 'spamprotect'
        remTime = self.bot.config[spamProtectTimer] - (time.time() - self.timers[cmd][target])
        if remTime > 0:
            self.bot.privmsg(mask.nick, "Wait another " + str(int(remTime)) + " seconds before trying again.")
            return True
        self.timers[cmd][target] = time.time()
        return False

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

    def __isInChannel(self, player, channel):
        if player in channel:
            return True
        return False

    def __filterForPlayersInChannel(self, playerlist, channelname):
        players = {}
        if not channelname in self.bot.channels:
            return players
        channel = self.bot.channels[channelname]
        for p in playerlist.keys():
            if self.__isInChannel(p, channel):
                players[p] = True
        return players

    def __getNextDictIncremental(self, dict):
        for i in range(0, 99999999):
            if not dict.get(str(i), False):
                return str(i)
        return "-1"

    @command(permission='admin', public=False)
    @asyncio.coroutine
    def quote(self, mask, target, args):
        """Adds/removes a given quote from the quotelist.
        "{sender}" in the reply text will be replaced by the name of the person who triggered the response.

            %%quote get
            %%quote add TEXT ...
            %%quote del <ID>
        """
        return self.__genericCommandManage(mask, target, args, ['quotes'])

    def __getRandomDictKeys(self, dict, amount):
        """
        Returns a list of <amount> random elements, a maximum number depending on <amount> and dict size.
        """
        amount = min([len(dict), amount])
        keys = [key for key in dict.keys()]
        perm = np.random.permutation(keys)
        return [perm[i] for i in range(0, amount)]

    def __getRandomDictElements(self, dict, amount):
        """
        Returns a list of <amount> random elements, a maximum number depending on <amount> and dict size.
        """
        amount = min([len(dict), amount])
        keys = [key for key in dict.keys()]
        perm = np.random.permutation(keys)
        return [dict[perm[i]] for i in range(0, amount)]

    @command
    @asyncio.coroutine
    def shape(self, mask, target, args):
        """Say a quote

            %%shape
        """
        self.__genericSpamCommand(mask, target, args, ['quotes'])

    def __chooseMaps(self, listname, amount):
        list, exists = self.__getList(listname)
        if exists:
            maps = list.get('maps', {})
            return self.__getRandomDictKeys(maps, amount)
        return False

    @command
    @asyncio.coroutine
    def map(self, mask, target, args):
        """Pick a random map

            %%map <listname>
        """
        if self.spam_protect('map-'+mask.nick, mask, target, args):
            return
        listname = args.get("<listname>")
        maps = self.__chooseMaps(listname, 1)
        if maps:
            self.bot.privmsg(target, "I have chosen: " + maps[0])

    @command
    @asyncio.coroutine
    def bo3(self, mask, target, args):
        """Pick 3 random maps

            %%bo3 <listname>
        """
        if self.spam_protect('bo-'+mask.nick, mask, target, args):
            return
        listname = args.get("<listname>")
        maps = self.__chooseMaps(listname, 3)
        if maps:
            self.bot.privmsg(target, "I have chosen: " + ", ".join(maps))

    @command
    @asyncio.coroutine
    def bo5(self, mask, target, args):
        """Pick 5 random maps

            %%bo5 <listname>
        """
        if self.spam_protect('bo-'+mask.nick, mask, target, args):
            return
        listname = args.get("<listname>")
        maps = self.__chooseMaps(listname, 5)
        if maps:
            self.bot.privmsg(target, "I have chosen: " + ", ".join(maps))

    @command
    @asyncio.coroutine
    def lists(self, mask, target, args):
        """Show all map lists

            %%lists
        """
        if self.spam_protect('lists', mask, target, args):
            return
        lists = self.__dbGet(['maplists'])
        if len(lists) < 1:
            self.bot.privmsg(target, "There are no realms to explore.")
        else:
            msg = "Currently existing realms: "
            msg += ", ".join([name for name in lists])
            self.bot.privmsg(target, msg)

    @command
    @asyncio.coroutine
    def maplist(self, mask, target, args):
        """Show the list of maps

            %%maplist <listname>
        """
        listname = args.get("<listname>")
        list, exists = self.__getList(listname)
        if not exists:
            self.bot.privmsg(mask.nick, "Fool, there is no realm of such name. Insignificant.")
            return
        maps = list.get('maps', {})
        if len(maps) < 1:
            self.bot.privmsg(mask.nick, "This realm has yet to take form.")
            return
        self.bot.privmsg(mask.nick, str(len(maps)) + " maps are found in this realm:")
        self.bot.privmsg(mask.nick, ", ".join(maps))

    @command
    @asyncio.coroutine
    def owner(self, mask, target, args):
        """Show the owner of a map list

            %%owner <listname>
        """
        listname = args.get("<listname>")
        if self.spam_protect('owner-'+listname, mask, target, args):
            return
        list, exists = self.__getList(listname)
        if not exists:
            self.bot.privmsg(target, "There is no such realm.")
        else:
            admins = list.get('admins', {})
            text = "{name} reigns over this domain."
            if len(admins) > 0:
                text += " There are others who may guide you in there: "
                text += ", ".join([name for name in admins.keys()])
            self.bot.privmsg(target, text.format(**{
                    "name" : list.get('owner', 'The shaper')
                }))

    def __getList(self, listname):
        list = self.__dbGet(['maplists', listname])
        return list, len(list) > 0

    def __getMapsInList(self, listname):
        return [name for name in self.__dbGet(['maplists', listname, 'maps']).keys()]

    def __isListOwner(self, listname, playername):
        return self.__dbGet(['maplists', listname]).get('owner', '') == playername

    def __isListAdmin(self, listname, playername):
        return self.__dbGet(['maplists', listname]).get('admins', {}).get(playername, False)

    @command(public=False)
    @asyncio.coroutine
    def list(self, mask, target, args):
        """Manage a map list

            %%--- Only owner: ---
            %%list rename <listname> <newlistname>
            %%list del <listname>

            %%--- Owner and admin: ---
            %%list map get <listname>
            %%list map add <listname> <mapnames> ...
            %%list map del <listname> <mapnames> ...
            %%list admin add <listname> <playername>
            %%list admin del <listname> <playername>
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        rename, delete, add, get, admin, map, listname, newlistname, playername, mapnames \
            = args.get("rename"), args.get("del"), args.get("add"), args.get("get"), args.get("admin"), args.get("map"),\
              args.get("<listname>"), args.get("<newlistname>"), args.get("<playername>"), " ".join(args.get("<mapnames>"))
        isOwner, isAdmin = self.__isListOwner(listname, mask.nick), self.__isListAdmin(listname, mask.nick)

        list, exists = self.__getList(listname)
        if not exists:
            return "You fool. This realm exists only in your head."

        maps = mapnames.split(', ')

        if isOwner or isAdmin:
            if map:
                if add:
                    for name in maps:
                        self.__dbAdd(['maplists', listname, 'maps'], name, True)
                    return "Tried adding " + str(len(maps)) + " maps from your domain."
                if delete:
                    for name in maps:
                        self.__dbDel(['maplists', listname, 'maps'], name)
                    return "Tried removing " + str(len(maps)) + " maps from your domain."
                if get:
                    maps = self.__getMapsInList(listname)
                    if len(maps) < 1:
                        return "This realm has yet to take form."
                    self.bot.privmsg(mask.nick, str(len(maps)) + " maps are found in this realm:")
                    for map in maps:
                        self.bot.privmsg(mask.nick, map)
                    return

            if admin:
                if add:
                    self.__dbAdd(['maplists', listname, 'admins'], playername, True)
                    return playername + " was added to the list of your servants."
                if delete:
                    self.__dbDel(['maplists', listname, 'admins'], playername)
                    return playername + " will serve you no longer, and was banished from your domain."

            if isAdmin and rename:
                return "Do not meddle with your master's wishes, foolish mortal."

        if isOwner:
            if rename:
                _, newnameexists = self.__getList(newlistname)
                if newnameexists:
                    return "This name is already occupied. You shall not disturb this realm with your lack of knowledge."
                self.__dbAdd(['maplists'], newlistname, list.copy())
                self.__dbDel(['maplists'], listname)
                return "I have done as you requested."

            if delete:
                self.__dbDel(['maplists'], listname)
                return "It is done, the realm has vanished. Insignificant."

        return "You fool. This realm is not meant for you, and you shall not disturb it."

    @command
    @asyncio.coroutine
    def music(self, mask, target, args):
        """Say a music quote

            %%music
        """
        self.__genericSpamCommand(mask, target, args, ['music', 'general'], specialSpamProtect='spamprotect_music')

    @command(permission='admin', public=False)
    @asyncio.coroutine
    def music_(self, mask, target, args):
        """Adds/removes a given text from the quotelist.

            %%music_ get
            %%music_ add TEXT ...
            %%music_ del <ID>
        """
        return self.__genericCommandManage(mask, target, args, ['music', 'general'])

    @command
    @asyncio.coroutine
    def powermetal(self, mask, target, args):
        """Say a powermetal music quote

            %%powermetal
        """
        self.__genericSpamCommand(mask, target, args, ['music', 'powermetal'], specialSpamProtect='spamprotect_music')

    @command(permission='admin', public=False)
    @asyncio.coroutine
    def powermetal_(self, mask, target, args):
        """Adds/removes a given text from the quotelist.

            %%powermetal_ get
            %%powermetal_ add TEXT ...
            %%powermetal_ del <ID>
        """
        return self.__genericCommandManage(mask, target, args, ['music', 'powermetal'])

    @command(permission='admin')
    @asyncio.coroutine
    def reol(self, mask, target, args):
        """Say a reol music quote

            %%reol
        """
        self.__genericSpamCommand(mask, target, args, ['music', 'reol'], specialSpamProtect='spamprotect_music')

    @command(permission='admin', public=False)
    @asyncio.coroutine
    def reol_(self, mask, target, args):
        """Adds/removes a given text from the quotelist.

            %%reol_ get
            %%reol_ add TEXT ...
            %%reol_ del <ID>
        """
        return self.__genericCommandManage(mask, target, args, ['music', 'reol'])

    def __genericSpamCommand(self, mask, target, args, path, specialSpamProtect=None):
        if self.spam_protect("-".join(path), mask, target, args, specialSpamProtect=specialSpamProtect):
            return
        elems = self.__getRandomDictElements(self.__dbGet(path), 1)
        if len(elems) > 0:
            self.bot.privmsg(target, elems[0])

    def __genericCommandManage(self, mask, target, args, path, allowSameValue=False):
        """
        Generic managing of adding/removing/getting
        Needs: add,del,get,<ID>,TEXT
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        add, delete, get, id, text = args.get('add'), args.get('del'), args.get('get'), args.get('<ID>'), " ".join(args.get('TEXT'))
        dict = self.__dbGet(path)
        if add:
            if not allowSameValue:
                entries = self.__dbGet(path)
                for e in entries.values():
                    if e == text:
                        return "This already exists, so it won't be added."
            try:
                id = self.__getNextDictIncremental(dict)
                self.__dbAdd(path, id, text)
                return 'Added to the list.'
            except:
                return "Failed adding."
        elif delete:
            try:
                if dict.get(id):
                    dict = self.__dbDel(path, id)
                    return 'Removed element of ID "{id}".'.format(**{
                            "id" : id,
                        })
                else:
                    return 'ID not found in the list.'
            except:
                return "Failed deleting."
        elif get:
            self.bot.privmsg(mask.nick, str(len(dict)) + " elements:")
            for id in dict.keys():
                self.bot.privmsg(mask.nick, '<%s>: %s' % (id, dict[id]))

    def __dbAdd(self, path, key, value, overwriteIfExists=True):
        cur = self.bot.db
        for p in path:
            if p not in cur:
                cur[p] = {}
            cur = cur[p]
        if overwriteIfExists:
            cur[key] = value
        elif not cur.get(key):
            cur[key] = value
        self.__dbSave()
        return cur

    def __dbDel(self, path, key):
        cur = self.bot.db
        for p in path:
            cur = cur.get(p, {})
        if not cur.get(key) is None:
            del cur[key]
            self.__dbSave()
        return cur

    def __dbGet(self, path):
        reply = self.bot.db
        for p in path:
            reply = reply.get(p, {})
        return reply

    def __dbSave(self):
        self.bot.db.set('misc', lastSaved=time.time())