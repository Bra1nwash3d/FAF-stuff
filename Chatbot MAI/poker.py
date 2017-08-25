import threading
import random
import asyncio
from timed_input_accumulator import timedInputAccumulatorThread
import time

useDebugPrint = False
TIMEOUT_SECONDS = 30  # increased by entryrequirement/10, max 2*
GAMECOST = 2.5  # percent of wins
GAMECOSTRECEIVER = '#poker'

cardToStringValue = {
    11 : 'J',
    12 : 'Q',
    13 : 'K',
    14 : 'A',
}
cardToStringType = {
    0 : '♡', # 'Heart',
    1 : '♢', # 'Diamond',
    2 : '♧', # 'Clubs',
    3 : '♤', # 'Spade',
}
cardEvalToStringType = {
    1 : 'the highest card',
    2 : 'one pair',
    3 : 'two pairs',
    4 : 'three of a kind',
    5 : 'a straight',
    6 : 'a flush',
    7 : 'a full house',
    8 : 'four of a kind',
    9 : 'a straight flush',
    10 : 'a Royal Straight Flush',
}
cardCommentsOnMatchvalue = {
    # highest card
    1 : ["Sometimes you just find 5$ on the street, this is the time",
         "Neither has anything, but one must win."],
    # pair
    2 : ["Everyone on FAF is single, not you this time!",
         "Sometimes you don't need that much luck.",
         "Just enough work to win."],
    # two pairs
    3 : ["Good job. You might not be as lucky next time.",
         "Crushed.",
         "One for every limb you got. Unless you don't."],
    # three of a kind
    4 : ["At least you have threesomes on FAF.",
         "OOOOOHHH BABY A TRIPPLE",
         "A good result, isn't it."],
    # straight
    5 : ["You might not be, but you got a straight.",
         "If only your life lined up just as neatly",
         "What a surprise!"],
    # flush
    6 : ["Enemy points flushed down the drain!",
         "Suited up. Classy result!",
         "Easy win."],
    # full house
    7 : ["Boom.",
         "When you and your squad get together",
         "That wasnt a bluff."],
    # four of a kind
    8 : ["When a threesome just doesnt satisfy you anymore.",
         "Are you kidding me?",
         "Squad of quad to crush the pot"],
    # straight flush
    9 : ["AND THIS... IS TO GO EVEN FURTHER BEYOND... AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHHHHHHHHHHHHHH",
         "ABSULUTE  MADMAN WOAH",
         "Flush... crushed"],
    # royal straight flush
    10 : ["We forgot to include a message for this. It seemed just too unlikely."],
}

class PokerTimer(threading.Thread):
    def __init__(self, callbackf, args, seconds):
        threading.Thread.__init__(self)
        self.daemon = True
        self.callbackf = callbackf
        self.args = args
        self.seconds = seconds

    def run(self):
        for i in range(self.seconds):
            time.sleep(1)
        self.callbackf(self.args)


class Poker:
    def __init__(self, bot, callbackf, chatpointsObj, chateventsObj, channel, maxpoints):
        self.lock = threading.Lock()
        self.chatpointsObj = chatpointsObj
        self.chateventsObj = chateventsObj
        self.bot = bot
        self.maxpoints = maxpoints
        self.callbackf = callbackf
        self.roundcosts = [0, 0, 0, int(maxpoints*1/20+0.5), int(maxpoints*1/20+0.5), int(maxpoints*1/10+0.5)]  # depending on number of known cards
        self.channel = channel
        self.timeoutSeconds = TIMEOUT_SECONDS + min([TIMEOUT_SECONDS, int(self.maxpoints/25)])
        self.chatpointsDefaultKey = 'p'
        self.chatpointsReservedKey = 'chatpoker-reserved'
        self.reset()

    def debugPrint(self, text):
        if useDebugPrint:
            print(text.encode('ascii', errors='backslashreplace'))

    def reset(self):
        self.gameIsRunning = True
        self.players = {}
        self.playerOrder = []
        self.nextPlayer = 0
        self.playersActionTaken = self.nextPlayer # for timer
        self.acceptingNewPlayers = True
        self.highestPoints = 0
        self.remainingCards = []
        for t in range(4):
            for v in range(2, 15):
                self.remainingCards.append((t, v))
        self.knownCards = 2
        _, self.midCards = self.__pickRandomCards(5)
        self.currentStake = 0
        self.starttime = 0 # changed when first round begins

    def getChannel(self):
        return self.channel

    def __pickRandomCards(self, amount):
        if amount > len(self.remainingCards):
            return False, []
        cards = []
        for i in range(amount):
            cards.append(self.remainingCards.pop(random.randint(0, len(self.remainingCards)-1)))
        return True, cards

    def __readableCardList(self, cards):
        return ", ".join([self.__readableCard(c) for c in cards])

    def __readableCard(self, card):
        t, v = card
        if v >= 11:
            v = cardToStringValue[v]
        t = cardToStringType[t]
        return str(v)+t

    def __outputToChat(self, channel, msg):
        #self.debugPrint(channel + ': ' + msg)
        self.bot.privmsg(channel, msg)

    def __cardsIsFlush(self, playercards):
        # return true/false, subset (at least 5), remaining
        cards = playercards + []
        for type in range(4):
            if sum([1 if t==type else 0 for t,v in cards]) >= 5:
                subset, remaining = [], []
                for t,v in cards:
                    if t==type: subset.append((t,v))
                    else: remaining.append((t,v))
                return True, subset, remaining
        return False, [], playercards

    def __cardsIsStraight(self, playercards):
        # return true/false, subset (at least 5), remaining
        # TODO Ace also counts as 1? then change to range(14, 4, -1)
        cards = playercards + []
        cards = sorted(cards, key=lambda v: v[1], reverse=True)
        for number in range(14, 5, -1):
            used = [False for i in range(len(cards))]
            for n in range(number, number-5, -1):
                for i in range(len(cards)):
                    t,v = cards[i]
                    if v==n:
                        used[i] = True
                        break
            if sum(used) >= 5:
                straight, remaining = [], []
                for i in range(len(cards)):
                    t,v = cards[i]
                    if used[i]: straight.append((t,v))
                    else: remaining.append((t,v))
                return True, straight, remaining
        return False, [], playercards

    def __cardsIsMultiple(self, playercards, count=2):
        # return true/false, subset (at least count), remaining
        cards = playercards + []
        for number in range(14, 1, -1):
            multiple, remaining = [], []
            for t,v in cards:
                if v==number: multiple.append((t,v))
                else: remaining.append((t,v))
            if len(multiple) >= count:
                return True, multiple, remaining
        return False, [], playercards

    def __cardsHighest(self, playercards):
        # returns highest card, remaining
        cards = playercards+[]
        hv, index = -1, -1
        for i in range(len(cards)):
            t, v = cards[i]
            if v > hv:
                hv = v
                index = i
        if index >= 0:
            card = cards.pop(index)
            return card, cards
        return (-1,-1), playercards

    def __evaluateHelper(self, mv, cardgroups):
        v, highest, rem = [mv], False, []
        for cg in cardgroups:
            rem = cg
            while (len(rem) > 0) and (len(v) < 6):
                highest, rem = self.__cardsHighest(rem)
                v.append(highest[1])
        return v

    def __evaluateCardsValue(self, playercards):
        # returns [value of match, value1 of match card, value2 of match card, value of highest card]
        cards = playercards + self.midCards
        isFlush, flushcards, _ = self.__cardsIsFlush(cards)
        isStraightFlush, sflushcards, _ = self.__cardsIsStraight(flushcards)
        highestSFlushCard, _ = self.__cardsHighest(sflushcards)
        isRoyalFlush = (highestSFlushCard[1] == 14)
        if isRoyalFlush and isStraightFlush:
            # royal straight flush
            return self.__evaluateHelper(10, [sflushcards])
        if isStraightFlush:
            # straight flush
            return self.__evaluateHelper(9, [sflushcards])
        isMultiple4, mult4cards, remaining = self.__cardsIsMultiple(cards, count=4)
        if isMultiple4:
            # four of a kind
            return self.__evaluateHelper(8, [mult4cards, remaining])
        isMultiple3, mult3cards, mult3remaining = self.__cardsIsMultiple(cards, count=3)
        if isMultiple3:
            isMultiple2, mult2cards, remaining = self.__cardsIsMultiple(mult3remaining, count=2)
            if isMultiple2:
                # full house
                return self.__evaluateHelper(7, [mult3cards, mult2cards])
        if isFlush:
            # regular flush
            return self.__evaluateHelper(6, [flushcards])
        isStraight, straightcards, remaining = self.__cardsIsStraight(cards)
        if isStraight:
            # regular straight
            return self.__evaluateHelper(5, [straightcards])
        if isMultiple3:
            # three of a kind
            return self.__evaluateHelper(4, [mult3cards, mult3remaining])
        isMultiple2, mult2cards, remaining = self.__cardsIsMultiple(cards, count=2)
        if isMultiple2:
            isMultiple2second, mult2secondCards, mult2secondremaining = self.__cardsIsMultiple(remaining, count=2)
            if isMultiple2second:
                # two pairs
                return self.__evaluateHelper(3, [mult2cards, mult2secondCards, mult2secondremaining])
            # one pair
            return self.__evaluateHelper(2, [mult2cards, remaining])
        return self.__evaluateHelper(1, [cards])

    def __gameEndComment(self, matchvalue, winnercount):
        if winnercount > 1:
            return random.sample(["And now kiss each other <3"], 1)[0]
        return random.sample(cardCommentsOnMatchvalue[matchvalue], 1)[0]

    def __onGameEnd(self):
        if not self.gameIsRunning:
            return
        self.gameIsRunning = False
        # score
        self.debugPrint("\nPOKER GAME OVER")
        winnername, bestcardsvalue, stake = self.playerOrder[0], 0, 0
        winners = self.playerOrder
        for name in self.players.keys():
            stake += self.players[name]['totalpoints']
        gamecosts = int(stake * GAMECOST / 100 + 0.5)
        if len(self.playerOrder) == 1:
            # just one remaining, don't show cards
            self.__outputToChat(self.channel, "Poker game over! {name} wins {stake} points!".format(**{
                'name' : winnername,
                'stake' : str(stake),
            }))
        else:
            # evaluate, find highest
            for name in self.playerOrder:
                self.players[name]['cardvalues'] = self.__evaluateCardsValue(self.players[name]['cards'])
            highestUsers = self.playerOrder+[]
            for i in range(len(self.players[self.playerOrder[0]]['cardvalues'])):
                if len(highestUsers) <= 1:
                    break
                nextHighestUsers = []
                highestValue = -1
                for name in highestUsers:
                    v = self.players[name]['cardvalues'][i]
                    if v > highestValue:
                        highestValue = v
                        nextHighestUsers = [name]
                    elif v == highestValue:
                        nextHighestUsers.append(name)
                highestUsers = nextHighestUsers
            winners = highestUsers
            winnername = highestUsers[0]
            winningtype = self.players[highestUsers[0]]['cardvalues'][0]
            stringFormat = {
                'name' : winnername,
                'stake' : str(stake),
                'type' : cardEvalToStringType[winningtype],
                'cards' : self.__readableCardList(self.players[highestUsers[0]]['cards']),
                'midcards' : self.__readableCardList(self.midCards),
                'comment' : self.__gameEndComment(winningtype, len(winners)),
            }
            if len(winners) == 1:
                # single winner
                self.__outputToChat(self.channel, "Poker game over! {name} wins {stake} points with {type}! [{cards} | {midcards}]! {comment}".format(**stringFormat))
            else:
                # multiple winner :O
                stake = int(stake / len(winners))
                gamecosts = int(gamecosts / len(winners))+1
                stringFormat['name'] = ", ".join(winners)
                stringFormat['stake'] = str(stake)
                self.__outputToChat(self.channel, "Poker game over! {name} win {stake} points each with {type}! {comment}".format(**stringFormat))
        # transfer points
        losersDict = {}
        winnersDict = {}
        for name in self.players.keys():
            self.debugPrint("Handling player " + name + ", count of winners: " + str(len(winners)))
            pointsLost = self.players[name]['totalpoints']
            dct = {name : pointsLost/len(winners)}
            for winner in winners:
                self.chatpointsObj.transferByIds(winner, dct, receiverKey=self.chatpointsDefaultKey, giverKey=self.chatpointsReservedKey, allowNegative=False, partial=False)
                self.chatpointsObj.transferByIds(winner, dct, receiverKey='chatpoker', giverKey='chatpoker', allowNegative=True, partial=False)
            # making up for game costs
            if name in winners:
                self.debugPrint(name + ' winning, so tipping ' + str(gamecosts) + ' to ' + GAMECOSTRECEIVER)
                dct = {name : gamecosts}
                self.chatpointsObj.transferByIds(GAMECOSTRECEIVER, dct, receiverKey=self.chatpointsDefaultKey, giverKey=self.chatpointsDefaultKey, allowNegative=False, partial=False)
                self.chatpointsObj.transferByIds(GAMECOSTRECEIVER, dct, receiverKey='chatpoker', giverKey='chatpoker', allowNegative=True, partial=False)
                winnersDict[name] = pointsLost
            else:
                losersDict[name] = pointsLost
            _, amount = self.chatpointsObj.transferBetweenKeysById(name, self.chatpointsReservedKey, self.chatpointsDefaultKey, 999999999999, partial=True)
        self.chateventsObj.addEvent('chatpoker', {
            'winners' : winnersDict,
            'stakepw' : stake,
            'losers' : losersDict,
            'gamecostspw' : gamecosts,
            'channel' : self.channel,
        })
        for name in self.players.keys():
            self.__outputToChat(name, "Poker game over! You have {} points now!".format(format(self.chatpointsObj.getById(name).get(self.chatpointsDefaultKey, 0), '.1f')))
        self.callbackf({
            'channel' : self.channel,
            'starttime' : self.starttime,
        })

    def beginNewRound(self):
        if self.knownCards >= len(self.midCards):
            self.__onGameEnd()
            return
        if len(self.playerOrder) <= 1:
            self.__onGameEnd()
            return
        #self.playerOrder = self.playerOrder[self.nextPlayer:] + self.playerOrder[:self.nextPlayer]
        self.nextPlayer = 0    # will be corrected when starting
        self.playersActionTaken = self.nextPlayer
        self.acceptingNewPlayers = False
        self.knownCards += 1
        self.currentStake = 0
        self.continuousCalls = 0
        for name in self.playerOrder:
            self.__updatePlayer(name, self.roundcosts[self.knownCards], wipeRoundPoints=True)
        pot = sum([v.get('totalpoints', 0) for v in self.players.values()])
        self.__outputToChat(self.channel, "Beginning new round! {pot} points in the pot! Known cards: [{cards}], Order is: [{order}]".format(**{
            "cards" : self.__readableCardList(self.midCards[:self.knownCards]),
            "order" : ", ".join(self.playerOrder),
            "pot" : str(pot),
        }))

    def beginFirstRound(self, name):
        if (self.knownCards < 3) and (name in self.playerOrder):
            self.starttime = time.time()
            order = self.playerOrder + []
            self.playerOrder = random.sample(order, len(order))
            self.beginNewRound()
            self.nextPlayer = -1
            self.__informNext(playerDropped=False)

    def __isPlayersTurn(self, name):
        if not self.gameIsRunning:
            self.__outputToChat(name, "The game is over!")
            return False
        if self.acceptingNewPlayers:
            self.__outputToChat(self.channel, "Still accepting new players! Patience please!")
            return False
        nextPlayer = self.playerOrder[self.nextPlayer]
        if not (name == nextPlayer):
            self.__outputToChat(self.channel, "It's {}'s turn!".format(nextPlayer))
            return False
        return True

    def __updatePlayer(self, name, points, wipeRoundPoints=False):
        if not self.players.get(name, False):
            self.__outputToChat(self.channel, "You aren't participating, {}!".format(name))
            return False, 0
        if (self.players[name]['totalpoints'] + points) > self.maxpoints:
            points = self.maxpoints - self.players[name]['totalpoints']
        self.players[name]['totalpoints'] += points
        self.players[name]['roundpoints'] += points
        if wipeRoundPoints:
            self.players[name]['roundpoints'] = 0
        self.debugPrint('+ updating player ' + name + ': ' + str(self.players[name]))
        return True, points

    def __informNext(self, playerDropped=False):
        if len(self.playerOrder) == 1:
            self.__onGameEnd()
            return
        if not playerDropped:
            self.nextPlayer += 1
            self.playersActionTaken += 1
        if self.nextPlayer >= len(self.playerOrder):
            self.nextPlayer = 0
        if self.continuousCalls == len(self.playerOrder):
            self.beginNewRound()
        nextPlayer = self.playerOrder[self.nextPlayer]
        missingPoints = self.__getNecessaryCallPoints(nextPlayer)
        if self.gameIsRunning:
            self.__outputToChat(nextPlayer, "Your turn! {missing} required to call! You have {points} left to bet! Timeout in {seconds} seconds!".format(**{
                'seconds' : self.timeoutSeconds,
                'points' : str(self.maxpoints - self.players[nextPlayer].get('totalpoints',0)),
                'missing' : str(missingPoints)
            }))
        PokerTimer(self.timeoutFold, {
            'name' : nextPlayer,
            'knowncards' : self.knownCards,
            'playersActionTaken' : self.playersActionTaken,
        }, self.timeoutSeconds).start()

    def __getNecessaryCallPoints(self, name):
        return self.currentStake - self.players[name]['roundpoints']

    def __reservePlayerPoints(self, name):
        worked, _ = self.chatpointsObj.transferBetweenKeysById(name, self.chatpointsDefaultKey, self.chatpointsReservedKey, self.maxpoints, partial=False)
        return worked

    def signup(self, name):
        # intended to have only one point value inserted here
        self.lock.acquire()
        if self.players.get(name, False):
            self.__outputToChat(name, "You already joined this round, {}!".format(name))
            self.lock.release()
            return False
        if not self.acceptingNewPlayers:
            self.__outputToChat(name, "Sorry, signup is closed!")
            self.lock.release()
            return False
        if not self.__reservePlayerPoints(name):
            self.__outputToChat(self.channel, "Sorry {name}, you require at least {points} points to join this game!".format(**{
                'name' : name,
                'points' : self.maxpoints,
            }))
            self.lock.release()
            return False
        worked, cards = self.__pickRandomCards(2)
        if worked:
            self.players[name] = {
                'totalpoints' : 0,
                'roundpoints' : 0,
                'cards' : cards,
                'out' : False,
            }
            self.playerOrder.append(name)
            self.__outputToChat(name, "You've joined the game! Your cards: [{}]".format(self.__readableCardList(cards)))
            self.__outputToChat(self.channel, "{name} joined the game! Playerlist: [{list}]".format(**{
                'name' : name,
                'list' : ', '.join(self.playerOrder),
            }))
        else:
            self.__outputToChat(self.channel, "No cards left!")
        if len(self.playerOrder) == 1:
            self.__outputToChat(self.channel, "A new poker game! Use '!cpoker join' to join, and '!cpoker start' to start it! Requires {} points to join!".format(self.maxpoints))
        self.lock.release()
        return True

    def __fold(self, name):
        if not self.__isPlayersTurn(name):
            return False
        self.__updatePlayer(name, 0, wipeRoundPoints=True)
        self.playerOrder.pop(self.nextPlayer)
        self.__informNext(playerDropped=True)
        return True

    def timeoutFold(self, args):
        self.lock.acquire()
        if not self.gameIsRunning:
            self.lock.release()
            return
        if args.get('knowncards', -1) < self.knownCards:
            self.lock.release()
            return
        if args.get('playersActionTaken', -1) < self.playersActionTaken:
            self.lock.release()
            return
        if not (args.get('name') in self.playerOrder):
            self.lock.release()
            return
        self.__outputToChat(self.channel, "{} folding by timeout!".format(args.get('name')))
        self.__fold(args.get('name'))
        self.lock.release()

    def fold(self, name):
        self.lock.acquire()
        r = self.__fold(name)
        if r:
            self.__outputToChat(name, "Fold confirmed")
        self.lock.release()
        return r

    def call(self, name):
        self.lock.acquire()
        if not self.__isPlayersTurn(name):
            self.lock.release()
            return False
        self.continuousCalls += 1
        missingPoints = self.__getNecessaryCallPoints(name)
        self.__updatePlayer(name, missingPoints, wipeRoundPoints=False)
        self.__informNext()
        self.__outputToChat(name, "Call confirmed")
        self.lock.release()
        return True

    def raise_(self, name, points):
        self.lock.acquire()
        if not self.__isPlayersTurn(name):
            self.lock.release()
            return False
        missingCallPoints = self.__getNecessaryCallPoints(name)
        missingPoints = missingCallPoints + points
        worked, paidPoints = self.__updatePlayer(name, missingPoints, wipeRoundPoints=False)
        raisedPoints = (paidPoints - missingCallPoints)
        if worked and (raisedPoints > 0):
            self.continuousCalls = 1
            self.currentStake += raisedPoints
            self.debugPrint(">>> Raised by " + str(raisedPoints))
            self.__outputToChat(self.channel, name + " raised by " + str(raisedPoints))
            self.__outputToChat(name, "Raise confirmed")
        else:
            self.continuousCalls += 1
            self.__outputToChat(self.channel, "Further raising not possible! Called instead.")
            self.__outputToChat(name, "Raising not possible, called instead")
        self.__informNext()
        self.lock.release()
        return True

    def reveal(self, name):
        if self.gameIsRunning:
            return False
        if self.players.get(name, False):
            self.__outputToChat(self.channel, name + "'s cards: " + self.__readableCardList(self.players[name]['cards']))
        return True

    def isRunning(self):
        return self.gameIsRunning