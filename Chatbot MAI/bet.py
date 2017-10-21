useDebugPrint = False

class Bet():

    def __init__(self, bot, chatpointsObj, chateventsObj, name, description, channel='#shadows'):
        self.bot = bot
        self.name = name
        self.chatpointsDefaultKey = 'p'
        self.chatpointsReservedKey = 'chatbet-reserved'
        self.chatpointsStatisticsKey = 'chatbets'
        self.channel = channel
        self.gamecostreceiver = '#shadows'
        self.chatpointsObj = chatpointsObj
        self.chateventsObj = chateventsObj
        self.description = description
        self.options = {}

    def __debugPrint(self, text):
        if useDebugPrint:
            print(text.encode('ascii', errors='backslashreplace'))

    def __outputToChat(self, channel, msg):
        self.__debugPrint(channel + ': ' + msg)
        self.bot.privmsg(channel, msg)

    def __addOptionIfNecessary(self, optionname):
        if not self.options.get(optionname, False):
            self.__debugPrint('adding option: ' + optionname)
            self.options[optionname] = {}

    def __addPlayerToOption(self, optionname, id, points):
        if points <= 0:
            return
        self.__addOptionIfNecessary(optionname)
        self.options[optionname][id] = self.options[optionname].get(id, 0) + points

    def __reservePlayerPoints(self, name, points, partial):
        return self.chatpointsObj.transferBetweenKeysById(name, self.chatpointsDefaultKey, self.chatpointsReservedKey, points, partial=partial)

    def addOptions(self, TEXT):
        for option in TEXT.lower().replace(",", " ").split():
            if len(option) >= 1:
                self.__addOptionIfNecessary(option)

    def asString(self):
        optionStrings = [key+" ("+str(sum(self.options[key].values()))+")" for key in self.options.keys()]
        return self.name + ": " + self.description + " [" + ", ".join(optionStrings) + "]"

    def addBet(self, channel, optionname, id, points, allpoints=False):
        self.__debugPrint('adding bet: ' + optionname + ', id=' + id + ', points=' + str(points) + ', allpoints=' + str(allpoints))
        if not optionname in self.options.keys():
            self.__outputToChat(channel, 'The selection option does not exist!')
            return False
        worked, amount = self.__reservePlayerPoints(id, points, partial=allpoints)
        if worked:
            self.__addPlayerToOption(optionname, id, amount)
            if allpoints:
                self.__outputToChat(channel, 'Noted! ('+str(amount)+' points)')
            else:
                self.__outputToChat(channel, 'Noted!')
            return True
        return False

    def endBet(self, winningoption):
        if not winningoption in self.options.keys():
            return False
        winning = {}
        all = {}
        for key in self.options.keys():
            option = self.options[key]
            if key == winningoption:
                for name in option.keys():
                    winning[name] = winning.get(name, 0) + option[name]
                    all[name] = all.get(name, 0) + option[name]
            else:
                for name in option.keys():
                    all[name] = all.get(name, 0) + option[name]
        winningpoints = sum(winning.values())
        losingpoints = sum(all.values())
        # first, all players send their lost points
        for name in all.keys():
            pointsLost = all[name]
            dct = {name : pointsLost}
            self.__debugPrint("Handling player " + name + ", sending " + str(pointsLost) + " points to gamecostreceiver")
            self.chatpointsObj.transferByIds(self.gamecostreceiver, dct, receiverKey=self.chatpointsDefaultKey, giverKey=self.chatpointsReservedKey, allowNegative=False, partial=False)
            self.chatpointsObj.transferByIds(self.gamecostreceiver, dct, receiverKey=self.chatpointsStatisticsKey, giverKey=self.chatpointsStatisticsKey, allowNegative=True, partial=False)
        for name in winning.keys():
            pointsWon = (winning[name] / winningpoints) * losingpoints
            pointsWon = int(pointsWon)
            dct = {self.gamecostreceiver : pointsWon}
            winning[name] = pointsWon
            self.__debugPrint("Handling winner " + name + ", sending " + str(pointsWon) + " points from gamecostreceiver")
            self.chatpointsObj.transferByIds(name, dct, receiverKey=self.chatpointsDefaultKey, giverKey=self.chatpointsDefaultKey, allowNegative=False, partial=False)
            self.chatpointsObj.transferByIds(name, dct, receiverKey=self.chatpointsStatisticsKey, giverKey=self.chatpointsStatisticsKey, allowNegative=True, partial=False)
        # stats
        self.chateventsObj.addEvent(self.chatpointsStatisticsKey, {
            'name' : self.name,
            'description' : self.description,
            'winners' : winning,
            'bets' : all,
        })
        # inform players
        for name in all.keys():
            self.__outputToChat(name, 'The bet "{name}" finished, winning option was "{winningoption}"! Your points changed by {diff}, you have a total of {total} points now.'.format(**{
                'name' : self.name,
                'winningoption' : winningoption,
                'diff' : format(winning.get(name, 0) - all.get(name, 0), '.1f'),
                'total' : format(self.chatpointsObj.getById(name).get(self.chatpointsDefaultKey, 0), '.1f'),
            }))
        # inform channel
        dct = {
            'name' : self.name,
            'winningoption' : winningoption,
            'points' : format(losingpoints, '.1f'),
            'winnercount' : str(len(winning.keys())),
            'count' : str(len(all.keys())),
        }
        if len(winning.keys()) >= 1:
            self.__outputToChat(self.channel, 'The bet "{name}" finished, winning option was "{winningoption}"! {points} points are distributed to {winnercount} winners, from {count} participants!'.format(**dct))
        else:
            self.__outputToChat(self.channel, 'The bet "{name}" finished, winning option was "{winningoption}"! Nobody won any of the {points} points!'.format(**dct))
        return True

