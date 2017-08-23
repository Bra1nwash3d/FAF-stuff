# vim: ts=4 et sw=4 sts=4
# -*- coding: utf-8 -*-
import random
import asyncio
import requests
import re

import irc3
from irc3.plugins.command import command
from irc3.plugins.async import Whois
import time
import threading
import os
import codecs
import traceback
import json
import shutil

from twitch import twitchThread
from timed_input_accumulator import timedInputAccumulatorThread
from periodic_callback import periodicCallback
from markov import Markov
from points import Points
from events import Events
from poker import Poker


MAIN_CHANNEL = "#aeolus" #   shadows
IGNOREDUSERS = {}
CDPRIVILEDGEDUSERS = {}
NICKSERVIDENTIFIEDRESPONSES = {}
NICKSERVRESPONSESLOCK = None
TIMERS = {}
DEFAULTCD = False

RENAMED_REGEX_NAMES = re.compile("<td>.*?</td>")
RENAMED_REGEX_CURRENTNAME = re.compile("<br /><b>.*?</b>")

CHATLVL_COMMANDLOCK = False
CHATLVL_RESETNAME = '#reset'
CHATLVL_NORESETNAME = '#noreset'
CHATLVL_NORESETDISCOUNT = 0.5
CHATLVL_RESETCOUNT = 25000
CHATLVL_EPOCH = 1
CHATLVLWORDS = {}
POINTS_PER_CHATLVL = 5
CHATLVL_TOPPLAYERS = {}
CHATPOINTS_REMOVAL_IF_KICKED = 100

useDebugPrint = False
useLSTM = False


@irc3.extend
def action(bot, *args):
    bot.privmsg(args[0], '\x01ACTION ' + args[1] + '\x01')

@irc3.plugin
class Plugin(object):

    requires = [
        'irc3.plugins.userlist',
    ]

    def __init__(self, bot):
        self.bot = bot
        self.timers = {}
        self.whois = Whois(bot)
        self.loop = asyncio.new_event_loop()
        #asyncio.set_event_loop(self.loop)
        #self.oldHelp = self.help
        global NICKSERVRESPONSESLOCK, CHATLVL_COMMANDLOCK
        CHATLVL_COMMANDLOCK = threading.Lock()
        NICKSERVRESPONSESLOCK = threading.Lock()

    def debugPrint(self, text):
        if useDebugPrint:
            print(text)

    @classmethod
    def reload(cls, old):
        return cls(old.bot)

    @irc3.event(irc3.rfc.CONNECTED)
    def nickserv_auth(self, *args, **kwargs):
        self.bot.privmsg('nickserv', 'identify %s' % self.bot.config['nickserv_password'])
        self.on_restart()

    @irc3.event(irc3.rfc.JOIN)
    def on_join(self, channel, mask):
        #print('join', channel, mask)
        global CHATLVL_TOPPLAYERS
        if CHATLVL_TOPPLAYERS.get(mask.nick, False):
            if mask.nick == self.bot.config['nick']:
                return
            self.bot.action(channel, "Behold! {name}, currently rank {rank} on the chatlvl ladder, joined this chat!".format(**{
                "name" : mask.nick,
                "rank" : str(CHATLVL_TOPPLAYERS.get(mask.nick, -1))
            }))
        pass

    def __addText(self, text):
        try:
            self.TEXT += str(text.encode('ascii', 'ignore')) + "\n"
            l = len(self.TEXT)
            self.TEXT = self.TEXT[max([l-40,0]):l]
        except Exception:
            #print(traceback.format_exc())
            pass

    @irc3.event(irc3.rfc.PRIVMSG)
    @asyncio.coroutine
    def on_privmsg(self, *args, **kwargs):
        msg, channel, sender = kwargs['data'], kwargs['target'], kwargs['mask']
        if self.bot.config['nick'] in sender.nick:
            return
        if sender.startswith("NickServ!"):
            self.__handleNickservMessage(msg)
            return
        #if not msg.startswith('!'):
        #    self.__addText(msg)
        global IGNOREDUSERS, MAIN_CHANNEL
        if channel == MAIN_CHANNEL and "undress MAI" in msg:
            if not self.spam_protect("undress", "setoner", MAIN_CHANNEL, args):
                self.bot.action(channel, "blushes and reveals http://i.imgur.com/IOnpStK.png")
            return
        if channel.startswith("#") and not sender.nick in IGNOREDUSERS.values():
            self.update_chatlevels(sender, channel, msg)
            #self.AeolusMarkov.addLine(msg)

    @irc3.event(irc3.rfc.KICK)
    @asyncio.coroutine
    def on_kick(self, *args, **kwargs):
        kicktarget = kwargs['target']
        print('kick', kicktarget)
        global CHATPOINTS_REMOVAL_IF_KICKED
        if not (kicktarget == self.bot.config['nick']):
            self.Chatevents.addEvent('kick', {
                'target' : kicktarget,
                'points' : CHATPOINTS_REMOVAL_IF_KICKED
            })
            self.Chatpoints.updatePointsById(kicktarget, -CHATPOINTS_REMOVAL_IF_KICKED, partial=True)

    @irc3.event(irc3.rfc.MODE)
    @asyncio.coroutine
    def on_mode(self, *args, **kwargs):
        print('MODE ', args, kwargs)
        """
        MODE  () {'modes': '+b', 'target': '#shadows', 'event': 'MODE', 'mask': 'Washy!Washy@Clk-4A328548.hsi13.unitymediagroup.de', 'data': '*!*@<ip/provider>'}
        -b
        """
        pass

    @asyncio.coroutine
    def __isNickservIdentified(self, nick):
        self.bot.privmsg('nickserv', "status {}".format(nick))
        remainingTries = 20
        while remainingTries > 0:
            if NICKSERVIDENTIFIEDRESPONSES.get(nick):
                value = NICKSERVIDENTIFIEDRESPONSES[nick]
                NICKSERVRESPONSESLOCK.acquire()
                del NICKSERVIDENTIFIEDRESPONSES[nick]
                NICKSERVRESPONSESLOCK.release()
                if int(value) == 3:
                    return True
                return False
            remainingTries -= 1
            yield from asyncio.sleep(0.1)
        return False

    def __handleNickservMessage(self, message):
        message = " ".join(message.split())
        NICKSERVRESPONSESLOCK.acquire()
        if message.startswith('STATUS'):
            words = message.split(" ")
            NICKSERVIDENTIFIEDRESPONSES[words[1]] = words[2]
        NICKSERVRESPONSESLOCK.release()

    """
    @command
    @asyncio.coroutine
    def help(self, mask, target, args):
        "" "Spam protected help

            %%help
        "" "
        if self.spam_protect("help", mask.nick, target, args):
            return
        commands = ["chain", "chainb", "chainf", "chainprob", "rearrange", "chatlvl", "chattip", "chatstats", "chatroulette/cbet"]
        return ", ".join(commands)
        #yield from command.help(args)"""

    @command(permission='admin', show_in_help_list=False, public=False)
    @asyncio.coroutine
    def restart(self, mask, target, args):
        """Restart stuff

            %%restart
        """
        self.on_restart()
        return "Restarted"

    def on_restart(self):
        time.clock()
        t0 = time.clock()
        global TIMERS, IGNOREDUSERS, DEFAULTC, CDPRIVILEDGEDUSERS, DEFAULTCD
        global CHATLVLWORDS,  CHATLVLEVENTDATA, CHATLVL_TOPPLAYERS, CHATLVL_EPOCH
        DEFAULTCD = self.bot.config.get('spam_protect_time', 600)
        self.__dbAdd([], 'ignoredusers', {}, overwriteIfExists=False, save=False)
        self.__dbAdd([], 'cdprivilege', {}, overwriteIfExists=False, save=False)
        for t in ['chain', 'chainprob', 'rearrange', 'twitchchain', 'generate', 'chattip', 'chatlvl', 'chatladder', 'chatgames']:
            self.__dbAdd(['timers'], t, DEFAULTCD, overwriteIfExists=False, save=False)
        self.__dbAdd([], 'chatlvltopplayers', {}, overwriteIfExists=False, save=False)
        self.__dbAdd([], 'chatlvlwords', {}, overwriteIfExists=False, save=False)
        self.__dbAdd(['chatlvlmisc'], 'epoch', 1, overwriteIfExists=False, save=True)
        IGNOREDUSERS = self.__dbGet(['ignoredusers'])
        CHATLVL_TOPPLAYERS = self.__dbGet(['chatlvltopplayers'])
        TIMERS = self.__dbGet(['timers'])
        CHATLVLWORDS = self.__dbGet(['chatlvlwords'])
        CHATLVLWORDS = self.__dbGet(['chatlvlwords'])
        CDPRIVILEDGEDUSERS = self.__dbGet(['cdprivilege'])
        CHATLVL_EPOCH = self.__dbGet(['chatlvlmisc', 'epoch'])
        self.AeolusMarkov = Markov(self, self.bot.config.get('markovwordsstorage_chat', './dbmarkovChat.json'))
        self.ChangelogMarkov = Markov(self, self.bot.config.get('markovwordsstorage_changelog', './dbmarkovChangelogs.json'))
        self.Chatpoints = Points(self.bot.config.get('chatlevelstorage', './chatlevel.json'))
        self.Chatevents = Events(self.bot.config.get('chateventstorage', './chatevents.json'))
        self.Chatpoker = False

        try:
            self.chatroulettethread.stop()
            self.timedSavingThread.stop()
            self.twitchthread.stop()
        except:
            pass
        self.chatroulettethread = False
        self.timedSavingThread = periodicCallback(self.save, isAsyncioCallback=False,
                                                  args={'path' : 'auto/', 'keep' : 72},
                                                  seconds=self.bot.config.get('autosave', 300))
        self.timedSavingThread.start()
        self.twitchthread = False

        if useLSTM:
            from LSTMGen import LSTMGen
            self.LSTMGen = LSTMGen(self.bot)
        self.TEXT = ""

        t1 = time.clock()
        print("Startup time: {t}".format(**{"t" : format(t1-t0, '.4f')}))

    @command(permission='admin', show_in_help_list=False)
    @asyncio.coroutine
    def join(self, mask, target, args):
        """Overtake the given channel

            %%join <channel>
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        self.bot.join(args['<channel>'])

    @command(permission='admin', show_in_help_list=False)
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

    @command(show_in_help_list=False, public=False)
    @asyncio.coroutine
    def list(self, mask, target, args):
        """List <count> people in channel, starting at <offset>

            %%list <channel> <offset> <count>
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        channel, offset, count = args['<channel>'], int(args['<offset>']), int(args['<count>'])
        channellist = sorted([user for user in self.bot.channels[channel]])
        channellist.pop(0)
        if offset > len(channellist):
            self.bot.privmsg(mask.nick, "Offset > amount of people in channel ({total})".format(**{
                "total" : str(len(channellist)),
            }))
            return
        NAMES_PER_PM = 30
        self.bot.privmsg(mask.nick, "Listing {count} of {total} people in {channel}:".format(**{
                "count" : str(min([count,len(channellist)])),
                "total" : str(len(channellist)),
                "channel" : channel,
            }))
        i = offset
        while True:
            self.bot.privmsg(mask.nick, ", ".join(channellist[i:min([i + NAMES_PER_PM, len(channellist), offset + count])]))
            i += NAMES_PER_PM
            if i >= offset + count:
                break

    @command(permission='admin', public=False, show_in_help_list=False)
    @asyncio.coroutine
    def twitchjoin(self, mask, target, args):
        """Join given twitch channel

            %%twitchjoin <channel>
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        self.createTwitchConIfNecessary()
        self.twitchthread.join(args.get('<channel>'))

    @command(permission='admin', public=False, show_in_help_list=False)
    @asyncio.coroutine
    def twitchleave(self, mask, target, args):
        """Leave given twitch channel

            %%twitchleave <channel>
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        self.createTwitchConIfNecessary()
        self.twitchthread.leave(args.get('<channel>'))

    @command(permission='admin', public=False, show_in_help_list=False)
    @asyncio.coroutine
    def twitchstop(self, mask, target, args):
        """Ends all twitch connections

            %%twitchstop
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        if self.twitchthread:
            self.twitchthread.stop()
        self.twitchthread = False

    @command(permission='admin', public=False, show_in_help_list=False)
    @asyncio.coroutine
    def twitchmsg(self, mask, target, args):
        """Write to the given twitch channel

            %%twitchmsg <channel> TEXT ...
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        self.createTwitchConIfNecessary()
        #self.twitchthread.join(args.get('<channel>'))
        self.twitchthread.message(args.get('<channel>'), " ".join(args.get('TEXT')))

    def createTwitchConIfNecessary(self):
        if not self.twitchthread:
            self.twitchthread = twitchThread(self.bot, self, self.AeolusMarkov)
            self.twitchthread.start()

    @command(permission='admin', show_in_help_list=False, public=False)
    @asyncio.coroutine
    def files(self, mask, target, args):
        """ To read files, no abuse please

            %%files get
            %%files parse log <chat/changelog> <filename>
            %%files parse raw <chat/changelog> <filename>
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        get, parse, log, raw, filename, chatchangelog = args.get('get'), args.get('parse'), args.get('log'), args.get('raw'), args.get('<filename>'), args.get('<chat/changelog>')
        if get:
            for dirname, dirnames, filenames in os.walk('./files'):
                for filename in filenames:
                    self.bot.privmsg(mask.nick, ' - ' + filename)
        if parse:
            try:
                filename = "./files/" + filename
                filetype = "LOG"
                if raw:
                    filetype = "RAW"
                if chatchangelog == "chat":
                    self.AeolusMarkov.addFile(filename, filetype=filetype)
                elif chatchangelog == "changelog":
                    self.ChangelogMarkov.addFile(filename, filetype=filetype)
                else:
                    self.bot.privmsg(mask.nick, '<chat/changelog> needs to be either "chat" or "changelog".')
                self.bot.privmsg(mask.nick, 'Succeeded parsing. Use !savedb to save progress.')
            except Exception:
                print(traceback.format_exc())
                self.bot.privmsg(mask.nick, 'Failed parsing.')

    @command(permission='admin', show_in_help_list=False)
    @asyncio.coroutine
    def cd(self, mask, target, args):
        """ Set cooldowns

            %%cd get
            %%cd get <timer>
            %%cd set <timer> <time>
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        get, set, timer, time = args.get('get'), args.get('set'), args.get('<timer>'), args.get('<time>')
        global TIMERS, DEFAULTCD
        if get:
            if timer:
                self.bot.privmsg(mask.nick, 'The cooldown for "' + timer + '" is set to ' + str(TIMERS.get(timer, DEFAULTCD)))
            else:
                for key in TIMERS.keys():
                    self.bot.privmsg(mask.nick, 'The cooldown for "' + key + '" is set to ' + str(TIMERS.get(key, DEFAULTCD)))
        if set:
            TIMERS[timer] = int(time)
            self.__dbAdd(['timers'], timer, TIMERS[timer], save=True)
            self.bot.privmsg(mask.nick, 'The cooldown for "' + timer + '" is now changed to ' + str(TIMERS[timer]))

    @command(permission='admin', public=False, show_in_help_list=False)
    @asyncio.coroutine
    def savedb(self, mask, target, args):
        """ Saves to the db, takes a while, no abuse please

            %%savedb
            %%savedb all
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        all = args.get('all')
        t0 = time.clock()
        args = {
            'saveAeolusMarkov' : all,
            'saveChangelogMarkov' : all,
            'path' : 'manual/',
            'keep' : 5,
        }
        self.save(args)
        t1 = time.clock()
        self.bot.privmsg(mask.nick, "Saving completed. ({t} seconds)".format(**{"t" : format(t1-t0, '.4f')}))

    def save(self, args={}):
        self.__dbSave()
        self.Chatpoints.save()
        self.Chatevents.save()
        path = './backups/'+args.get('path', '')
        pathFull = path+str(int(time.time()))+"/"
        os.makedirs(pathFull, exist_ok=True)
        shutil.copy2("./"+self.Chatpoints.getFilePath(), pathFull) # chatpoint backup
        shutil.copy2("./"+self.Chatevents.getFilePath(), pathFull)
        allRelevantBackups = [d[0] for d in os.walk(path)]
        for i in range(1, len(allRelevantBackups) - args.get('keep', 10)):
            shutil.rmtree(allRelevantBackups[i])
        if args.get('saveAeolusMarkov', False):
            self.AeolusMarkov.save()
        if args.get('saveChangelogMarkov', False):
            self.ChangelogMarkov.save()
        return True

    def chatreset(self):
        global CHATLVL_EPOCH
        if not self.chatroulettethread:
            self.save(args = {
                'path' : 'reset/'+str(CHATLVL_EPOCH)+'/',
                'keep' : 100000,
            })
            self.Chatpoints.reset()
            self.Chatevents.reset()
            CHATLVL_EPOCH += 1
            self.save(args = {
                'path' : 'post-reset/',
                'keep' : 5,
            })
            self.__dbAdd(['chatlvlmisc'], 'epoch', CHATLVL_EPOCH, overwriteIfExists=True, save=True)

    @command(permission='admin')
    @asyncio.coroutine
    def ignore(self, mask, target, args):
        """ Change the ignore list

            %%ignore get
            %%ignore add TEXT ...
            %%ignore del <ID>
        """
        response = self.__genericCommandManage(mask, target, args, ['ignoredusers'])
        global IGNOREDUSERS
        IGNOREDUSERS = self.__dbGet(['ignoredusers'])
        return response

    @command(permission='admin', public=False, show_in_help_list=False)
    @asyncio.coroutine
    def cdprivilege(self, mask, target, args):
        """ Change the cdprivilege list, which shortens individual cooldowns

            %%cdprivilege get
            %%cdprivilege add <name> <time>
            %%cdprivilege del <name>
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        add, delete, get, t, name = args.get('add'), args.get('del'), args.get('get'), args.get('<time>'), args.get('<name>')
        global CDPRIVILEDGEDUSERS
        if add:
            try:
                CDPRIVILEDGEDUSERS, _, _ = self.__dbAdd(['cdprivilege'], name, int(t), save=True)
                return "Added"
            except:
                return "Failed"
        if get:
            self.bot.privmsg(mask.nick, str(len(CDPRIVILEDGEDUSERS)) + " users:")
            for id in CDPRIVILEDGEDUSERS.keys():
                self.bot.privmsg(mask.nick, '%s: %s' % (id, CDPRIVILEDGEDUSERS[id]))
        if delete:
            CDPRIVILEDGEDUSERS = self.__dbDel(['cdprivilege'], name, save=True)
            return "Removed"

    @command(permission='admin', public=False, show_in_help_list=False)
    @asyncio.coroutine
    def chatlvlwords(self, mask, target, args):
        """ Change the cdprivilege list, which shortens individual cooldowns

            %%chatlvlwords get
            %%chatlvlwords add <points> TEXT ...
            %%chatlvlwords addm <points> TEXT ...
            %%chatlvlwords del TEXT ...
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        add, addm, delete, get, points, text = args.get('add'), args.get('addm'), args.get('del'), args.get('get'), args.get('<points>'), " ".join(args.get('TEXT'))
        global CHATLVLWORDS
        if add or addm:
            try:
                p = int(points)
                if addm:
                    p *= -1
                CHATLVLWORDS, _, _ = self.__dbAdd(['chatlvlwords'], text, p, save=False)
                return "Added"
            except:
                return "Failed"
        if get:
            self.bot.privmsg(mask.nick, str(len(CHATLVLWORDS)) + " words:")
            words = ['"%s": %s' % (id, CHATLVLWORDS[id]) for id in CHATLVLWORDS.keys()]
            self.bot.privmsg(mask.nick, ', '.join(words))
        if delete:
            CHATLVLWORDS = self.__dbDel(['chatlvlwords'], text, save=False)
            return "Removed"

    @command()
    @asyncio.coroutine
    def rearrange(self, mask, target, args):
        """Rearrange letters in words

            %%rearrange TEXT ...
        """
        if self.spam_protect('rearrange', mask, target, args, specialSpamProtect='rearrange'):
            return
        words = args.get('TEXT')
        for i in range(0,len(words)):
            if len(words[i]) > 2 and (not self.isInChannel(words[i], target)):
                w = words[i]
                wh = w[1:len(w)-1]
                words[i] = w[0] + ''.join(random.sample(wh, len(wh))) + w[len(w)-1]
        self.bot.privmsg(target, " ".join(words))

    @command()
    @asyncio.coroutine
    def changelog(self, mask, target, args):
        """ See what the future will bring

            %%changelog
        """
        if self.spam_protect('changelog', mask, target, args, specialSpamProtect='changelog'):
            return
        self.bot.privmsg(target, self.ChangelogMarkov.forwardSentence(False, 30, target, includeWord=True))

    @command()
    @asyncio.coroutine
    def chain(self, mask, target, args):
        """ Chain words both directions <3

            %%chain <word>
        """
        if self.spam_protect('chain', mask, target, args, specialSpamProtect='chain'):
            return
        #l = 30
        #lf = random.randint(MINCHAINLENGTH/2, l - MINCHAINLENGTH/2)
        #lb = l - lf
        word = args.get('<word>', False)
        forward = self.AeolusMarkov.forwardSentence(word, 20, target, includeWord=False)
        backward = self.AeolusMarkov.backwardSentence(word, 20, target, includeWord=True)
        self.bot.privmsg(target, backward + forward)

    if useLSTM:
        @command(public=False)
        @asyncio.coroutine
        def generate(self, mask, target, args):
            """ Generate a text based on LSTMs

                %%generate
                %%generate TEXT ...
            """
            if self.spam_protect('generate', mask, target, args, specialSpamProtect='generate'):
                return
            text =  " ".join(args.get('TEXT'))
            if text:
                self.__addText(text)
            gen = self.LSTMGen.generate(self.TEXT, 0.4, 100)
            self.bot.privmsg(target, gen)

    @command()
    @asyncio.coroutine
    def chainf(self, mask, target, args):
        """ Chain words forwards <3

            %%chainf
            %%chainf <word>
        """
        if self.spam_protect('chain', mask, target, args, specialSpamProtect='chain'):
            return
        word = args.get('<word>', False)
        self.bot.privmsg(target, self.AeolusMarkov.forwardSentence(word, 30, target, includeWord=True))

    @command()
    @asyncio.coroutine
    def chainb(self, mask, target, args):
        """ Chain words backwards <3

            %%chainb <word>
        """
        if self.spam_protect('chain', mask, target, args, specialSpamProtect='chain'):
            return
        word = args.get('<word>', False)
        self.bot.privmsg(target, self.AeolusMarkov.backwardSentence(word, 30, target, includeWord=True))

    @command()
    @asyncio.coroutine
    def chainprob(self, mask, target, args):
        """ Retrieve the probability of words in order

            %%chainprob <word1>
            %%chainprob <word1> <word2>
        """
        if self.spam_protect('chainprob', mask, target, args, specialSpamProtect='chainprob'):
            return
        w1, w2 = args.get('<word1>'), args.get('<word2>')
        self.bot.privmsg(target, self.AeolusMarkov.chainprob(w1, w2))

    def update_chatlevels(self, mask, channel, msg):
        global CHATLVLWORDS, MAIN_CHANNEL
        points, text = 0, msg.lower()
        for word in CHATLVLWORDS.keys():
            if word in text:
                points += CHATLVLWORDS[word]
        wordcount = len(text.split())
        avglen = (len(msg)-wordcount+1) / wordcount
        if msg.startswith('!') or (avglen < 2):
            return
        points += min([0.4*wordcount, 1.2+0.2*wordcount, 6])
        if channel == MAIN_CHANNEL:
            self.Chatpoints.updatePointsById(mask.nick, points)
        if channel.startswith('#'):
            self.Chatpoints.updatePointsById(channel, points)

    def update_chatlvl(self, name, channel, points, addChangeTo=False):
        return self.Chatpoints.updatePointsById(name, points)

    def __chatLevelAndPoints(self, points):
        level = 1
        req = self.Chatpoints.getPointsForLevelUp(level)
        while points >= req:
            level += 1
            req = self.Chatpoints.getPointsForLevelUp(level)
        return level, points

    @command()
    @asyncio.coroutine
    def chatlvl(self, mask, target, args):
        """ Display chatlvl + points

            %%chatlvl
            %%chatlvl <name>
        """
        location = target
        if self.spam_protect('chatlvl', mask, target, args, specialSpamProtect='chatlvl', ircSpamProtect=False):
            location = mask.nick
        name = args.get('<name>', False)
        if not name:
            name = mask.nick
        data = self.Chatpoints.getPointDataById(name)
        tipstring, roulettestring = "", ""
        if data.get('chatroulette', False):
            roulettestring = ", " + str(format(data.get('chatroulette'), '.1f')) + " from chat roulette"
        if data.get('chatpoker', False):
            tipstring = ", " + str(format(data.get('chatpoker'), '.1f')) + " from chat poker"
        if data.get('chattip', False):
            tipstring = ", " + str(format(data.get('chattip'), '.1f')) + " from chat tips"
        self.bot.privmsg(location, "{object}'s level: {level}, points: {points} ({toUp} to next level, {total} in total){roulettestring}{tipstring}".format(**{
                "object": name,
                "level": str(data.get('level', 1)),
                "points": format(data.get('points', 1), '.1f'),
                "toUp": format(data.get('tonext', 1), '.1f'),
                "total": format(data.get('p', 1), '.1f'),
                "roulettestring": roulettestring,
                "tipstring": tipstring,
            }))

    @command()
    @asyncio.coroutine
    def chattip(self, mask, target, args):
        """ Tip some chatlvl points to someone <3

            %%chattip <name>
            %%chattip <name> <points/all>
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        global CHATLVL_COMMANDLOCK, CHATLVL_RESETNAME, CHATLVL_NORESETNAME, CHATLVL_RESETCOUNT, CHATLVL_NORESETDISCOUNT
        CHATLVL_COMMANDLOCK.acquire()
        self.debugPrint('commandlock acquire chattip')
        channel = target
        if self.spam_protect('chattip', mask, target, args, specialSpamProtect='chattip', ircSpamProtect=False):
            channel = mask.nick
        takername, points = args.get('<name>', False), args.get('<points/all>')
        givername = mask.nick
        """
        if takername in IGNOREDUSERS.values():
            self.bot.privmsg(mask.nick, "This user is on the ignore list and can not be tipped.")
            return
        """
        if not points:
            points = 5
        try:
            if not points == 'all':
                points = abs(int(points))
        except:
            self.bot.action(channel, "Failed to send points! Are you sure you gave me a number?")
            CHATLVL_COMMANDLOCK.release()
            self.debugPrint('commandlock release chattip 1')
            return
        _, points = self.Chatpoints.transferPointsByIdsSimple(takername, givername, points, partial=True, addTo='chattip')
        if points < 1:
            CHATLVL_COMMANDLOCK.release()
            self.debugPrint('commandlock release chattip 2')
            return

        self.Chatevents.addEvent('chattip', {
            'giver' : givername,
            'taker' : takername,
            'points' : points,
        })
        addstring = ""
        if takername in [CHATLVL_RESETNAME, CHATLVL_NORESETNAME]:
            p = self.Chatpoints.getPointsById(CHATLVL_RESETNAME)
            rp = self.Chatpoints.getPointsById(CHATLVL_NORESETNAME) * CHATLVL_NORESETDISCOUNT
            resetNeeded = CHATLVL_RESETCOUNT + rp
            addstring = "{p} of {max} points for a reset collected!".format(**{
                "p": format(p, '.1f'),
                "max": str(resetNeeded),
            })
            channel = target
            if takername == CHATLVL_NORESETNAME:
                addstring = "Reset delayed! " + addstring
            elif (takername == CHATLVL_RESETNAME) and (p > resetNeeded):
                addstring = "Enough points to reset collected! RESETTING NOW!"
                self.chatreset()
        self.bot.action(channel, "{giver} tipped {p} points to {taker}! {add}".format(**{
                "giver": givername,
                "p": format(points, '.1f'),
                "taker": takername,
                "add": addstring,
            }))
        CHATLVL_COMMANDLOCK.release()
        self.debugPrint('commandlock release chattip eof')

    @asyncio.coroutine
    def __maskToFafId(self, mask):
        return mask.nick, True #TODO
        try:
            return str(mask.host.split('@')[0]), True
        except:
            return "-1", False

    @asyncio.coroutine
    def __nameToFafId(self, name):
        return name, True #TODO
        global MAIN_CHANNEL, CHATLVLS
        if name.startswith('#'):
            return name, True
        if not self.isInChannel(name, MAIN_CHANNEL):
            for v in CHATLVLS.keys():
                if CHATLVLS[v].get('n', False) == name:
                    #print('not in main, but v:', v)
                    return v, True
            return "-1", False
        whois = yield from self.whois(nick=name)
        return whois.get('username', False), whois.get('timeout', True) == False

    @command()
    @asyncio.coroutine
    def chatladder(self, mask, target, args):
        """ The names of the top ladder warriors

            %%chatladder
            %%chatladder all
            %%chatladder tip
            %%chatladder tip rev
            %%chatladder roulette
            %%chatladder roulette rev
        """
        tip, roulette, rev, all = args.get('tip'), args.get('roulette'), args.get('rev', False), args.get('all', False)
        if self.spam_protect('chatladder', mask, target, args, specialSpamProtect='chatladder'):
            return
        global CHATLVLS, CHATLVL_TOPPLAYERS
        ladder = []
        announceString = ""
        individualString = ""
        default = (not tip) and (not roulette)
        if tip:
            ladder = self.Chatpoints.getSortedBy(by='chattip', reversed=(not rev))
            announceString = "Top tip receivers (received-sent): {list}"
            if rev:
                announceString = "Top tip givers (received-sent): {list}"
            individualString = "{name} with {chattip} points"
        elif roulette:
            ladder = self.Chatpoints.getSortedBy(by='chatroulette', reversed=(not rev))
            announceString = "Top roulette winners (won-lost): {list}"
            if rev:
                announceString = "Unlucky roulette players (won-lost): {list}"
            individualString = "{name} with {chatroulette} points"
        elif default:
            ladder = self.Chatpoints.getSortedBy(by='p', reversed=True)
            announceString = "Top chatwarriors: {list}"
            individualString = "{name} (level {level})"
        announcePlayers = []
        top5 = {}
        announced = 0
        for i in range(len(ladder)):
            playerdata = self.Chatpoints.getPointDataById(ladder[i][0])
            name = playerdata.get('n','-')
            if all or (not (name.startswith('#') or name in IGNOREDUSERS.values())):
                announcePlayers.append(individualString.format(**{
                    "name": self.getUnpingableName(playerdata.get('n','-')),
                    "level": playerdata.get('level', 0),
                    "chattip": format(playerdata.get('chattip', 0), '.1f'),
                    "chatroulette": format(playerdata.get('chatroulette', 0), '.1f'),
                }))
                announced += 1
                top5[name] = announced
                if announced >= 5:
                    break
        if default and not all:
            CHATLVL_TOPPLAYERS = top5
            self.__dbAdd([], 'chatlvltopplayers', CHATLVL_TOPPLAYERS, overwriteIfExists=True, trySavingWithNewKey=False, save=True)
        self.bot.privmsg(target, announceString.format(**{
                "list": ", ".join(announcePlayers),
            }))

    @command()
    @asyncio.coroutine
    def chatstats(self, mask, target, args):
        """ The names of the top ladder warriors

            %%chatstats
            %%chatstats roulette
            %%chatstats roulette <name>
            %%chatstats roulette minplayers <playercount>
        """
        roulette, minplayers, name, playercount = args.get('roulette'), args.get('minplayers'), args.get('<name>'), args.get('<playercount>')
        channel = target
        if self.spam_protect('chatstats', mask, target, args, specialSpamProtect='chatstats'):
            channel = mask.nick
        if roulette:
            rouletteevents = []
            if name:
                id = name # to change
                for game in self.Chatevents.getData('chatroulette'):
                    if game['bets'].get(id, False):
                        rouletteevents.append(game)
            elif minplayers:
                try:
                    playercount = int(playercount)
                except:
                    playercount = 2
                for game in self.Chatevents.getData('chatroulette'):
                    if len(game['bets']) >= playercount:
                        rouletteevents.append(game)
            else:
                rouletteevents = self.Chatevents.getData('chatroulette')
            if len(rouletteevents) == 0:
                return "There are 0 events to talk about!"
            totalpoints = 0
            highestwin, highestwinner = 0, ""
            roibet, roiwin, roiratio, roiwinner = 0, 1, 0, ""
            gamecount = max([len(rouletteevents), 1])
            for game in rouletteevents:
                gametotal = sum(game['bets'].values()) - game['bets'].get(self.bot.config['nick'], 0)
                totalpoints += gametotal
                gamewinner = game['winner']
                gameroiratio = gametotal / game['bets'].get(gamewinner, 999999999)
                if gametotal > highestwin:
                    highestwin = gametotal
                    highestwinner = gamewinner
                if (gameroiratio > roiratio) and not (gamewinner == self.bot.config['nick']):
                    roiratio = gameroiratio
                    roibet = game['bets'].get(game['winner'], 999999999)
                    roiwin = gametotal
                    roiwinner = gamewinner
            winnername = self.Chatpoints.getById(highestwinner)['n']
            hwinnername = self.getUnpingableName(winnername)
            roiname = self.Chatpoints.getById(roiwinner)['n']
            roiwinnername = self.getUnpingableName(roiname)
            self.bot.action(channel, "Chatroulette stats! Total games: {count}, total points bet: {totalpoints}, average points per game: {avg}, "\
                                    "highest stake game: {hpoints} points won by {hwinner}, "\
                                    "highest ROI game: (R={roiwin}; I={roibet}, ratio={roiratio}) by {roiwinner}".format(**{
                    "count": str(gamecount),
                    "totalpoints": str(totalpoints),
                    "avg": format(totalpoints / gamecount, '.1f'),
                    "hpoints": str(highestwin),
                    "hwinner": hwinnername,
                    "roibet": str(roibet),
                    "roiwin": str(roiwin),
                    "roiratio": format(roiratio, '.3f'),
                    "roiwinner": roiwinnername,
                }))
            return

    @command(permission='admin', public=False, show_in_help_list=False)
    @asyncio.coroutine
    def chatlvlpoints(self, mask, target, args):
        """ Add/remove points of player

            %%chatlvlpoints add <name> <points>
            %%chatlvlpoints remove <name> <points>
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        global CHATLVL_COMMANDLOCK
        CHATLVL_COMMANDLOCK.acquire()
        self.debugPrint('commandlock acquire chatlvlpoints')
        add, remove, name, points = args.get('add'), args.get('remove'), args.get('<name>'), args.get('<points>')
        try:
            points = int(points)
        except:
            self.bot.action(mask.nick, "Failed to send points! Are you sure you gave me a number?")
            points = 0
        if remove:
            points *= -1
        self.Chatpoints.updateById(name, delta={'p' : points}, allowNegative=False, partial=True)
        self.bot.action(mask.nick, "Done!")
        CHATLVL_COMMANDLOCK.release()
        self.debugPrint('commandlock release chatlvlpoints eof')

    @command(permission='admin', show_in_help_list=False)
    @asyncio.coroutine
    def chatslap(self, mask, target, args):
        """ Slap someone and remove some of his points

            %%chatslap <name>
            %%chatslap <name> <points>
        """
        if not (yield from self.__isNickservIdentified(mask.nick)):
            return
        global CHATLVL_COMMANDLOCK
        CHATLVL_COMMANDLOCK.acquire()
        self.debugPrint('commandlock acquire chatslap')
        name, points = args.get('<name>'), args.get('<points>')
        try:
            points = abs(int(points))
        except:
            points = 5
        self.Chatpoints.updateById(name, delta={'p' : -points}, allowNegative=False, partial=True)
        self.bot.action(target, "slaps {name}, causing him/her to lose {points} points".format(**{
                "name": name,
                "points": str(points),
            }))
        self.Chatevents.addEvent('chatslap', {
            'by' : mask.nick,
            'target' : name,
            'points' : points,
        })
        CHATLVL_COMMANDLOCK.release()
        self.debugPrint('commandlock release chatslap eof')

    @command(permission='admin', show_in_help_list=False, public=False)
    def chatgamesadmin(self, mask, target, args):
        """ To restore reserved points

            %%chatgamesadmin restore roulette
            %%chatgamesadmin restore poker
        """
        global CHATLVL_COMMANDLOCK
        CHATLVL_COMMANDLOCK.acquire()
        self.debugPrint('commandlock acquire chatgamesadmin')
        restore, roulette, poker = args.get('restore'), args.get('roulette'), args.get('poker')
        if restore:
            keyFrom, keyTo = 'reserved', 'p'
            if roulette:
                keyFrom = 'chatroulette-reserved'
            if poker:
                keyFrom = 'chatpoker-reserved'
            self.Chatpoints.transferBetweenKeysForAll(keyFrom, keyTo, 99999999999, deleteOld=False)
        self.bot.privmsg(mask.nick, "Done!")
        CHATLVL_COMMANDLOCK.release()
        self.debugPrint('commandlock release chatgamesadmin eof')

    @command
    @asyncio.coroutine
    def cpoker(self, mask, target, args):
        """ %%cpoker signup
            %%cpoker signup <points>
            %%cpoker fold
            %%cpoker call
            %%cpoker raise <points>
            %%cpoker start
        """
        if self.spam_protect('chatgames', mask, target, args, specialSpamProtect='chatgames', updateTimer=False):
            return
        global CHATLVL_COMMANDLOCK
        CHATLVL_COMMANDLOCK.acquire()
        if self.chatroulettethread:
            CHATLVL_COMMANDLOCK.release()
            return "Another game is in progress!"
        self.debugPrint('commandlock acquire chatpoker')
        signup, fold, call, raise_, points, start = args.get('signup'), args.get('fold'), args.get('call'), args.get('raise'), args.get('<points>'), args.get('start')
        if points:
            try:
                points = abs(int(points))
            except:
                CHATLVL_COMMANDLOCK.release()
                self.debugPrint('commandlock release chatpoker 1')
                return
        else:
            points = 50
        if not self.Chatpoker:
            self.Chatpoker = Poker(self.bot, self.on_cpoker_done, self.Chatpoints, self.Chatevents, target, points)
        if start:
            self.Chatpoker.beginFirstRound(mask.nick)
        if call:
            self.Chatpoker.call(mask.nick)
        if fold:
            self.Chatpoker.fold(mask.nick)
        if signup:
            self.Chatpoker.signup(mask.nick)
        if raise_:
            self.Chatpoker.raise_(mask.nick, points)
        CHATLVL_COMMANDLOCK.release()
        self.debugPrint('commandlock release chatpoker eof')

    def on_cpoker_done(self):
        self.Chatpoker = False
        self.spam_protect('chatgames', self.bot.config['nick'], MAIN_CHANNEL, {}, specialSpamProtect='chatgames', setToNow=True)
        self.save(args={
            'path' : 'poker/',
            'keep' : 5,
        })

    @command
    @asyncio.coroutine
    def cbet(self, mask, target, args):
        """ Shortcut to the chatroulette command

            %%cbet <points/all>
        """
        yield from self.chatroulette(mask, target, args)

    @command
    @asyncio.coroutine
    def chatroulette(self, mask, target, args):
        """ Play the chat point roulette! Bet points, 20s after the initial roll, a winner is chosen.
            Probability scales with points bet. The winner gets all points.

            %%chatroulette <points/all>
        """
        if self.spam_protect('chatgames', mask, target, args, specialSpamProtect='chatgames', updateTimer=False):
            return
        global CHATLVL_COMMANDLOCK
        CHATLVL_COMMANDLOCK.acquire()
        if self.Chatpoker:
            CHATLVL_COMMANDLOCK.release()
            return "Another game is in progress!"
        self.debugPrint('commandlock acquire chatroulette')
        points, use = args.get('<points/all>'), False
        allin = points in ["all", "allin"]
        if allin:
           points = 99999999999999
        else:
            try:
                points = abs(int(points))
            except:
                CHATLVL_COMMANDLOCK.release()
                self.debugPrint('commandlock release chatroulette 1')
                return
        worked, points = self.Chatpoints.transferBetweenKeysById(mask.nick, 'p', 'chatroulette-reserved', points, partial=allin)
        if not worked:
            self.bot.action(target, "You have too few points to bet this sum! ({name})".format(**{
                    "name": mask.nick,
                }))
            CHATLVL_COMMANDLOCK.release()
            self.debugPrint('commandlock release chatroulette 2')
            return
        points = int(points)
        if points < 1:
            CHATLVL_COMMANDLOCK.release()
            self.debugPrint('commandlock release chatroulette 3')
            return
        seconds = 20
        addedSeconds = min([10, points])  # to roulette timer
        if (not self.chatroulettethread):
            self.chatroulettethread = timedInputAccumulatorThread(callbackf=self.on_chatroulette_finished_noasync, args={"channel":target}, seconds=seconds, maxduration=60)
            self.chatroulettethread.start()
            self.bot.privmsg(target, "{name} is starting a chat roulette! Quickly, bet your points! ({seconds} seconds, betting is dangerous and can be addicting)".format(**{
                    "name": mask.nick,
                    "seconds": seconds,
                }))
        else:
            self.bot.action(mask.nick, "noted {name}'s bet (timer extended by {seconds} second(s))".format(**{
                    "name": mask.nick,
                    "seconds": str(addedSeconds),
                }))
        self.chatroulettethread.addInput((mask.nick, points), addSeconds=addedSeconds)
        if allin:
            self.bot.action(target, "{name} is going all in with {points} points!".format(**{
                    "name": mask.nick,
                    "points": str(points),
                }))
        CHATLVL_COMMANDLOCK.release()
        self.debugPrint('commandlock release chatroulette eof')

    def on_chatroulette_finished_noasync(self, args, inputs):
        self.loop.run_until_complete(self.on_chatroulette_finished(args, inputs))

    @asyncio.coroutine
    def on_chatroulette_finished(self, args, inputs):
        global CHATLVL_COMMANDLOCK
        CHATLVL_COMMANDLOCK.acquire()
        self.debugPrint('commandlock acquire roulettefinished')
        result = {}
        # let bot join the roulette... for free
        for i in inputs:
            result[i[0]] = result.get(i[0], 0) + i[1]
        totalpoints = sum(result.values())
        maibet = 1 + int(totalpoints/200)
        result[self.bot.config['nick']] = maibet
        winner, _ = self.pickWeightedRandom(result)
        print('- roulette done!', winner, args.get('channel'), totalpoints)
        print('- result: ', result)
        # winner print
        #TODO write stuff non-delayed :(
        if ((len(result) == 2 and maibet) or (len(result) == 1 and not maibet)) and (not (winner == self.bot.config['nick'])):
            self.bot.privmsg(args.get('channel'), 'The roulette ended without competition (points returned)')
        else:
            endstring = ""
            if winner == self.bot.config['nick']:
                endstring = random.choice(["Thanks for the tip :)", "Get rekt!", "HAHAHAHAHA!", "Thanks for the points!", "Thanks, losers >:)", "Thanks <3"])
            else:
                roi = totalpoints / result.get(winner, 1)
                if roi > 10:
                    endstring = random.choice(["Wew, lucky!", "Damn, so many points!", "Lucky! :)", "Congrats!"])
                elif roi > 3:
                    endstring = random.choice(["Surprising result!", "Nice!", "Well done!", "Lucky!", ":)", "Congrats!"])
                else:
                    endstring = random.choice(["Congratulations!", "Well done!", "As expected!", "The farming proceeds."])
            self.bot.privmsg(args.get('channel'), "The chat roulette ended! {name} won {totalpoints} points (bet: {bet})! {end}".format(**{
                    "name": winner,
                    "totalpoints": str(totalpoints),
                    "bet": str(result[winner]),
                    "end": endstring,
                }))
        # juggle points, remove MAI from the betting list
        del result[self.bot.config['nick']]
        self.Chatpoints.transferByIds(winner, result, receiverKey='p', giverKey='chatroulette-reserved', allowNegative=False, partial=False)
        self.Chatpoints.transferByIds(winner, result, receiverKey='chatroulette', giverKey='chatroulette', allowNegative=True, partial=False)
        #self.Chatpoints.transferBetweenKeysForAll('chatroulette-reserved', 'p', 99999999999, deleteOld=False) # recover original points which might lost to hickup etc
        # cooldown, data
        if self.chatroulettethread:
            self.chatroulettethread.stop()
            self.chatroulettethread = False
        self.Chatevents.addEvent('chatroulette', {
            'winner' : winner,
            'bets' : result
        })
        self.save(args={
            'path' : 'roulette/',
            'keep' : 5,
        })
        CHATLVL_COMMANDLOCK.release()
        self.debugPrint('commandlock release roulettefinished eof')
        self.spam_protect('chatgames', self.bot.config['nick'], args.get('channel'), args, specialSpamProtect='chatgames', setToNow=True)

    if False:
        @command(public=False, show_in_help_list=False)
        @asyncio.coroutine
        def maibotapi(self, mask, target, args):
            """ Enabling chat based data transfer

                %%maibotapi chatlvl <name>
                %%maibotapi pointcost <name> <points>
            """
            pass
            """
            if not (yield from self.__isNickservIdentified(mask.nick)):
                return
            print('MAIBOTAPI called by', mask.nick)
            if not (mask.nick in ["TheSetoner", "Giebmasse", "Giebmasse_irc", "Washy", "Purpleheart"]):
                print('abandoning')
                return
            chatlvl, pointcost, name, points = args.get('chatlvl'), args.get('pointcost'), args.get('<name>'), args.get('<points>', False)
            if points:
                try:
                    points = int(points)
                except:
                    self.bot.privmsg(mask.nick, "Failed: points not convertible to int")
                    return
            sid, data, use = -1, {}, False
            if chatlvl:
                self.update_chatlvl(mask.nick, mask.nick, 0)
                sid, data, use = yield from self.__chatlvlget(name=name)
                self.bot.privmsg(mask.nick, "{use}, level={level}, points={points}".format(**{
                        "use": str(use),
                        "level": str(data.get('l')),
                        "points": str(format(data.get('p', 0), '.1f')),
                    }))
                return
            if pointcost:
                use = self.update_chatlvl(name, name, -points)
                self.bot.privmsg(mask.nick, "{use}".format(**{
                        "use": str(use)
                    }))
                return
            self.bot.privmsg(mask.nick, "Failed")
            """

    @command(permission='admin', show_in_help_list=False)
    @asyncio.coroutine
    def maitest(self, mask, target, args):
        """ Test functionality

            %%maitest <name>
        """
        self.Chatpoints.merge("test54", "Washy")
        """
        name = args.get('<name>')
        #print('.')
        whois = yield from self.whois(nick=name)
        print(whois.get('username', False))
        return
        self.bot.action(target, "{msg}".format(**{
                "msg": "<3",
            }))
        """

    @command(public=False)
    @asyncio.coroutine
    def helpirenamed(self, mask, target, args):
        """ Merges data that's attached to your previous name to your current.

            %%helpirenamed
        """
        global RENAMED_REGEX_NAMES, RENAMED_REGEX_CURRENTNAME
        # try:
        r = requests.post("http://app.faforever.com/faf/userName.php", data={'name': mask.nick})
        data = RENAMED_REGEX_NAMES.findall(r.text)
        renames = []
        for i in range(int(len(data) / 2)):
            name = data[i * 2]
            until = data[i * 2 + 1]
            d = {
                'name': name[4:len(name) - 5],
                'until': until[4:len(until) - 5],
            }
            renames.append(d)
        if len(renames) <= 1:
            self.bot.privmsg(mask.nick, 'You have not changed your name, or FAF does not know about you.')
            return
        else:
            currentName = renames[-1]['name']
            previousName = renames[-2]['name']
            r = requests.post("http://app.faforever.com/faf/userName.php", data={'name': previousName})
            r2 = RENAMED_REGEX_CURRENTNAME.findall(r.text)
            if len(r2) == 0:
                self.bot.privmsg(mask.nick, 'Your previous nickname (' + previousName + ') seems to be taken.')
                return
            if (str(r2[0][9:len(r2[0])-4]) == str(mask.nick)) and (str(mask.nick) == str(currentName)):
                self.bot.privmsg(mask.nick, 'Confirmed! Merging with data of ' + previousName + '!')
                self.Chatpoints.merge(mask.nick, previousName)
            else:
                self.bot.privmsg(mask.nick, 'Something went wrong! :(')

    def getUnpingableName(self, name):
        return name[0:len(name)-1] + '.' + name[len(name)-1]

    def spam_protect(self, cmd, mask, target, args, updateTimer=True, specialSpamProtect=None, ircSpamProtect=True, setToNow=False):
        if setToNow:
            if not cmd in self.timers:
                self.timers[cmd] = {}
            self.timers[cmd][target] = time.time()
            return
        nick = mask
        if type(mask) is not str:
            nick = mask.nick
        if nick in IGNOREDUSERS.values():
            if ircSpamProtect:
                self.bot.privmsg(nick, "You are on the ignore list, commands will not be executed.")
            return True
        if ircSpamProtect:
            if target != MAIN_CHANNEL:
                return False
        if not cmd in self.timers:
            self.timers[cmd] = {}
        if not target in self.timers[cmd]:
            self.timers[cmd][target] = 0
        global TIMERS, DEFAULTCD, CDPRIVILEDGEDUSERS
        timer = TIMERS.get(specialSpamProtect,
                           self.bot.config.get(specialSpamProtect,
                                               DEFAULTCD))
        remTime = timer - (time.time() - self.timers[cmd][target]) - CDPRIVILEDGEDUSERS.get(nick, 0)
        if remTime > 0:
            if ircSpamProtect:
                self.bot.privmsg(nick, "Wait another " + str(int(remTime)+1) + " seconds before trying again.")
            return True
        if updateTimer:
            self.timers[cmd][target] = time.time()
        return False

    def pickWeightedRandom(self, dct):
        total = sum(dct.values())
        v = random.random() * total
        for key in dct.keys():
            v -= dct[key]
            if v <= 0:
                return key, total
        return dct.keys()[len(dct)-1], total

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
        add, delete, get, id, text = args.get('add'), args.get('del'), args.get('get'), args.get('<ID>'), " ".join(
            args.get('TEXT'))
        dict = self.__dbGet(path)
        if add:
            if not allowSameValue:
                entries = self.__dbGet(path)
                for e in entries.values():
                    if e == text:
                        return "This already exists, so it won't be added."
            try:
                id = self.__getNextDictIncremental(dict)
                self.__dbAdd(path, id, text, save=True)
                return 'Added to the list.'
            except:
                return "Failed adding."
        elif delete:
            try:
                if dict.get(id):
                    dict = self.__dbDel(path, id, save=True)
                    return 'Removed element of ID "{id}".'.format(**{
                        "id": id,
                    })
                else:
                    return 'ID not found in the list.'
            except:
                return "Failed deleting."
        elif get:
            self.bot.privmsg(mask.nick, str(len(dict)) + " elements:")
            for id in dict.keys():
                self.bot.privmsg(mask.nick, '<%s>: %s' % (id, dict[id]))

    def isInChannel(self, player, channel):
        if isinstance(channel, str):
            channel = self.bot.channels[channel]
        if player in channel:
            return True
        return False

    def __filterForPlayersInChannel(self, playerlist, channelname):
        players = {}
        if not channelname in self.bot.channels:
            return players
        channel = self.bot.channels[channelname]
        for p in playerlist.keys():
            if self.isInChannel(p, channel):
                players[p] = True
        return players

    def __getNextDictIncremental(self, dict):
        for i in range(0, 99999999):
            if not dict.get(str(i), False):
                return str(i)
        return "-1"

    @command(permission='admin', public=False)
    @asyncio.coroutine
    def hidden(self, mask, target, args):
        """Actually shows hidden commands
            %%hidden
        """
        words = ["join", "leave", "files", "cd", "savedb", "twitchjoin", "twitchleave",\
                 "twitchmsg", "list", "ignore", "cdprivilege",\
                 "chatlvlwords", "chatlvlpoints", "chatslap", "maibotapi", "restart", "chatgamesadmin"]
        self.bot.privmsg(mask.nick, "Hidden commands (!help <command> for more info):")
        #for word in words:
        #    self.bot.privmsg(mask.nick, "- " + word)
        self.bot.privmsg(mask.nick, ", ".join(words))

    def __dbAdd(self, path, key, value, overwriteIfExists=True, trySavingWithNewKey=False, save=True):
        cur = self.bot.db
        for p in path:
            if p not in cur:
                cur[p] = {}
            cur = cur[p]
        exists, addedWithNewKey = cur.get(key), False
        if overwriteIfExists:
            cur[key] = value
        elif not exists:
            cur[key] = value
        elif exists and trySavingWithNewKey:
            for i in range(0, 1000):
                if not cur.get(key+str(i)):
                    cur[key+str(i)] = value
                    addedWithNewKey = True
                    break
        if save:
            self.__dbSave()
        return cur, exists, addedWithNewKey

    def __dbDel(self, path, key, save=True):
        cur = self.bot.db
        for p in path:
            cur = cur.get(p, {})
        if not cur.get(key) is None:
            del cur[key]
            if save:
                self.__dbSave()
        return cur

    def __dbGet(self, path):
        reply = self.bot.db
        for p in path:
            reply = reply.get(p, {})
        return reply

    def __dbSave(self):
        self.bot.db.set('misc', lastSaved=time.time())