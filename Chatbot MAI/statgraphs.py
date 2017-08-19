import json
import numpy as np
from points import Points
import matplotlib.pyplot as plt

def plotPointsByLevel(chatpointsObj, points):
    yToNextLevel, yLevel = [], []
    for p in points:
        level, remaining, toNext = chatpointsObj.getLevelRemainingNextWithPoints(p)
        yToNextLevel.append(toNext)
        yLevel.append(level)
    plt.plot(points, yLevel, 'b')
    #plt.plot(points, yToNextLevel, 'r')
    plt.xlabel("Points")
    plt.ylabel("")
    plt.hlines([10*i for i in range(11)], points[0], points[-1])
    plt.legend(['Level'])
    plt.show()

def plotListAsHist(lst, legendString, firstElements=5, lastElements=5, groupRest=True, sort=True):
    if len(lst) == 0:
        return
    if sort:
        lst = sorted(lst, reverse=True, key=lambda v: v[1])
    lstTop = lst[:firstElements]
    lst = lst[firstElements:]
    bottomStart = max([(len(lst)-lastElements),0])
    lstBottom = lst[bottomStart:]
    lstRest = lst[:bottomStart]
    lst = lstTop
    if len(lstRest) > 0 and groupRest:
        lst.append(('Others (' + str(len(lstRest)) + ')', sum(v[1] for v in lstRest)))
    lst += lstBottom
    x = np.arange(len(lst))
    plt.bar(x, height=[lst[i][1] for i in range(len(x))])
    plt.xticks(x, [lst[i][0] for i in range(len(x))])
    plt.hlines([0], x[0]-0.5, x[-1]+0.5)
    plt.legend([legendString])
    plt.show()

def plotChattipsForName(chatevents, name, firstElements=5, lastElements=5):
    tippers = {}
    for tip in chatevents.get('chattip', {}):
        if tip.get('taker', '') == name:
            tippers[tip['giver']] = tippers.get(tip['giver'], 0) + tip['points']
        if tip.get('giver', '') == name:
            tippers[tip['taker']] = tippers.get(tip['taker'], 0) - tip['points']
    plotListAsHist([(k, tippers.get(k, 0)) for k in tippers.keys()], name + "'s sponsors",
                   firstElements=firstElements, lastElements=lastElements)

def filterChannels(lst):
    filteredLst = []
    for element in lst:
        if element[0].startswith('#'):
            continue
        filteredLst.append(element)
    return filteredLst

def plotMost(chatpointsObj, legendString, by='p', ignoreChannels=True, firstElements=10, lastElements=0, reversed=True):
    ladder = chatpointsObj.getSortedBy(by, reversed=reversed)
    if ignoreChannels:
        plotListAsHist(filterChannels(ladder), legendString + " (no channels)", firstElements=firstElements, lastElements=lastElements)
        return
    plotListAsHist(ladder, legendString, firstElements=firstElements, lastElements=lastElements)

def plotMostPoints(chatpointsObj, ignoreChannels=True, firstElements=10):
    return plotMost(chatpointsObj, "Most points", by='p', ignoreChannels=ignoreChannels, firstElements=firstElements)

def plotGamblersTipreceivers(chatpointsObj, ignoreChannels=True, firstElements=10, reversed=False):
    ladder = chatpointsObj.getSortedByMultiple(byPositive=['chatroulette', 'chattip'], byNegative=[], reversed=reversed)
    legendString = "Tips + roulette"
    if ignoreChannels:
        plotListAsHist(filterChannels(ladder), legendString + " (no channels)", firstElements=10, lastElements=0, groupRest=False, sort=False)
        return
    plotListAsHist(ladder, legendString, firstElements=firstElements, lastElements=0, groupRest=False, sort=False)

chatpoints = Points("./chatlevel.json")
chatpoints.transferBetweenKeysForAll('chatroulette-reserved', 'p', 99999999999, deleteOld=True)
chatpoints.save()
chatevents = {}
with open("./chatevents.json", 'r+') as file:
    chatevents = json.load(file)
#plotChattipsForName(chatevents, 'jarikboygangela')
#plotChattipsForName(chatevents, 'MAI')
#plotChattipsForName(chatevents, '#reset', firstElements=5, lastElements=0)
#plotMostPoints(chatpoints, firstElements=10, ignoreChannels=True)
plotMost(chatpoints, "Chattips ", by='chattip', firstElements=6, lastElements=6, ignoreChannels=True)
#plotMost(chatpoints, "Chatroulette ", by='chatroulette', firstElements=6, lastElements=6, ignoreChannels=True)
#plotPointsByLevel(chatpoints, range(25000))
#plotGamblersTipreceivers(chatpoints, ignoreChannels=True, reversed=True)

