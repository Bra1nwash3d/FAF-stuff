import json
import numpy as np
from points import Points
import matplotlib.pyplot as plt

def plotPointsByLevel(chatpointsObj, points):
    y1, y2 = [], []
    for p in points:
        level, remaining, toNext = chatpointsObj.getLevelRemainingNextWithPoints(p)
        y1.append(level)
        y2.append(level + remaining/toNext)
    plt.plot(points, y1, 'r')
    plt.plot(points, y2, 'b')
    plt.xlabel("Points")
    plt.ylabel("")
    plt.legend(['Level', 'Level including remaining points'])
    plt.show()

def plotListAsHist(lst, legendString, firstElements=5, lastElements=5):
    lst = sorted(lst, reverse=True, key=lambda v: v[1])
    lstTop = lst[:firstElements]
    lst = lst[firstElements:]
    lstBottom = lst[(len(lst)-lastElements):]
    lstRest = lst[:(len(lst)-lastElements)]
    lst = lstTop
    if len(lstRest) > 0:
        lst.append(('Others (' + str(len(lstRest)) + ')', sum(v[1] for v in lstRest)))
    lst += lstBottom
    x = np.arange(len(lst))
    plt.bar(x, height=[lst[i][1] for i in range(len(x))])
    plt.xticks(x, [lst[i][0] for i in range(len(x))])
    plt.legend([legendString])
    plt.show()

def plotChattipsForName(chatevents, name, firstElements=5, lastElements=5):
    tippers = {}
    for tip in chatevents.get('chattip', {}):
        if tip.get('taker', '') == name:
            tippers[tip['giver']] = tippers.get(tip['giver'], 0) + tip['points']
        if tip.get('giver', '') == name:
            tippers[tip['taker']] = tippers.get(tip['taker'], 0) - tip['points']
    plotListAsHist([(k, tippers.get(k, 0)) for k in tippers.keys()], 'Top ' + name + ' supporters',
                   firstElements=firstElements, lastElements=lastElements)

def plotMost(chatpointsObj, legendString, by='p', ignoreChannels=True, firstElements=10, reversed=True):
    ladder = chatpointsObj.getSortedBy(by, reversed=reversed)
    if ignoreChannels:
        filteredLadder = []
        for element in ladder:
            if element[0].startswith('#'):
                continue
            filteredLadder.append(element)
        plotListAsHist(filteredLadder, legendString + " (no channels)", firstElements=firstElements, lastElements=0)
        return
    plotListAsHist(ladder, legendString, firstElements=firstElements, lastElements=0)

def plotMostPoints(chatpointsObj, ignoreChannels=True, firstElements=10):
    return plotMost(chatpointsObj, "Most points", by='p', ignoreChannels=ignoreChannels, firstElements=firstElements)


chatpoints = Points("./chatlevel.json")
chatevents = {}
with open("./chatevents.json", 'r+') as file:
    chatevents = json.load(file)
plotChattipsForName(chatevents, 'jarikboygangela')
#plotChattipsForName(chatevents, '#reset')
#plotMostPoints(chatpoints, firstElements=10, ignoreChannels=True)
#plotPointsByLevel(chatpoints, range(25000))

