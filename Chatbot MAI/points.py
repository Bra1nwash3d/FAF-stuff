import json
import threading
import time

POINTS_PER_CHATLVL = 5



class Points():
    def __init__(self, jsonpath):
        self.jsonpath = jsonpath
        self.elements = {}
        self.add_lock = threading.Lock()
        self.update_lock = threading.Lock()
        try:
            with open(self.jsonpath, 'r+') as file:
                self.elements = json.load(file)
        except:
            pass

    def getPointsForLevelUp(self, level):
        if level <= 0:
            return 0
        return level * POINTS_PER_CHATLVL

    def save(self, path=False):
        if not path:
            path = self.jsonpath
        with open(path, 'w+') as file:
            json.dump(self.elements, file, indent=2)
            file.close()

    def reset(self):
        self.update_lock.acquire()
        self.elements = {}
        self.update_lock.release()

    def getIdByName(self, name):
        for key in self.elements.keys():
            if self.elements[key]['n'] == name:
                return key
        return name

    def getById(self, id):
        return self.elements.get(id, self.__getNewDefault())

    def getPointsById(self, id):
        return self.getById(id).get('p', 0)

    def getPointDataById(self, id):
        element = self.getById(id)
        level = 1
        toLevelUp = POINTS_PER_CHATLVL
        remaining = element.get('p', 0)
        for i in range(999999):
            if remaining < toLevelUp:
                toLevelUp = self.getPointsForLevelUp(level)
                break
            remaining -= toLevelUp
            level += 1
            toLevelUp = self.getPointsForLevelUp(level)
        return {
            'n' : element.get('n', '-'),
            'p' : element.get('p', 0),
            'level' : level,
            'points' : remaining,
            'tonext' : toLevelUp - remaining,
            'chatroulette' : element.get('chatroulette', False),
            'chattip' : element.get('chattip', False),
        }

    def addNew(self, id, name=False, data={}):
        """
        :param id: id of new element, will become name unless specified otherwise
        :param data: non default values
        """
        self.add_lock.acquire()
        if not name:
            name = id
        self.elements[id] = self.__getNewDefault(name)
        for key in data.keys():
            self.elements[id][key] = data[key]
        self.add_lock.release()

    def addNewIfNotExisting(self, id, name=False, data={}):
        if not self.elements.get(id, False):
            self.addNew(id, name=name, data=data)
        return self.elements[id]

    def __getNewDefault(self, name="-"):
        return {
            'n' : name,         # name
            'p' : 0,            # points
            't' : time.time()   # time of last update
        }

    def updateById(self, id, data={}, delta={}, allowNegative=False, partial=False):
        """
        Returns false if delta causes a param to go <0
        :param id:
        :param data:
        :param delta:
        :return:
        """
        self.update_lock.acquire()
        if not self.elements.get(id, False):
            self.addNew(id)
        self.addNewIfNotExisting(id, data=data)
        self.elements[id]['t'] = time.time()
        for key in delta.keys():
            new_value = self.elements[id].get(key, 0) + delta[key]
            if (new_value < 0) and (not allowNegative):
                if partial:
                    self.elements[id][key] = 0
                self.update_lock.release()
                return False
            self.elements[id][key] = new_value
            #if (new_value == 0):
            #    del self.elements[id][key]
        self.update_lock.release()
        return True

    def updatePointsById(self, id, points):
        return self.updateById(id, delta={'p' : points}, allowNegative=False)

    def transferBetweenKeysById(self, id, keyFrom, keyTo, amount, partial=False):
        """
        will not go negative
        """
        prevValue = self.addNewIfNotExisting(id).get(keyFrom, 0)
        if ((prevValue - amount) < 0):
            if (not partial):
                return False, 0
            amount = prevValue
        self.update_lock.acquire()
        self.elements[id][keyFrom] -= amount
        self.elements[id][keyTo] = self.elements[id].get(keyTo, 0) + amount
        self.update_lock.release()
        return True, amount

    def transferBetweenKeysForAll(self, keyFrom, keyTo, amount, deleteOld=True):
        """

        :param keyFrom:
        :param keyTo:
        :param amount: will be partially transfered by default, as much as possible
        :param deleteOld: removes old key from the dict
        :return:
        """
        self.update_lock.acquire()
        for id in self.elements.keys():
            p = min([amount, self.elements[id].get(keyFrom, 0)])
            self.elements[id][keyTo] = self.elements[id].get(keyTo, 0) + p
            self.elements[id][keyFrom] = 0
            if deleteOld:
                del self.elements[id][keyFrom]
        self.update_lock.release()

    def transferByIds(self, receiverId, giverIdDict, receiverKey='p', giverKey='p', allowNegative=False, partial=False):
        """
        Will do only partial transfer if single giver fail to hand in

        :param receiverId:
        :param giverIdDict: {id1 : 5, id2 : 10, ...}
        :param receiverKey:
        :param giverKey:
        :return:
        """
        toTransfer = 0
        for giverId in giverIdDict.keys():
            if self.updateById(giverId, delta={giverKey : -giverIdDict[giverId]}, allowNegative=allowNegative, partial=partial):
                toTransfer += giverIdDict[giverId]
        self.updateById(receiverId, delta={receiverKey : toTransfer})

    def transferPointsByIds(self, receiverId, giverIdDict):
        return self.transferByIds(receiverId, giverIdDict)

    def transferPointsByIdsSimple(self, receiverId, giverId, points, partial=True, addTo=False):
        """
        :param receiverId:
        :param giverId:
        :param points: number or 'all'
        :param partial:
        :return: if something was transfered, amount transfered
        """
        p = points
        if p == 'all':
            p = 9999999999999999
        if type(p) == str:
            return False, 0
        if partial:
            p = min([p, self.getPointsById(giverId)])
        if self.updatePointsById(giverId, -p):
            self.updatePointsById(receiverId, p)
            if addTo:
                self.updateById(giverId, delta={addTo : -p}, allowNegative=True)
                self.updateById(receiverId, delta={addTo : p}, allowNegative=True)
            return p > 0, p
        return False, p

    def getSortedBy(self, by='p', reversed=True):
        return sorted([(k, self.elements[k].get(by, 0)) for k in self.elements.keys()], reverse=reversed, key=lambda v: v[1])

    """
    def getByName(self, name):
        return self.elements.get(self.getIdByName(name), self.__getNewDefault(name=name))

    def updatePointsByName(self, name, points):
        return self.updateByName(name, delta={'p' : points}, allowNegative=False)

    def transferByNames(self, receiverName, giverNameDict, receiverKey='p', giverKey='p'):
        idDict = {}
        for giverName in giverNameDict.keys():
            idDict[self.getIdByName(giverName)] = giverNameDict[giverName]
        return self.transferByIds(self.getIdByName(receiverName), idDict, receiverKey=receiverKey, giverKey=giverKey)

    def transferPointsByNames(self, receiverName, giverNameDict):
        return self.transferByNames(receiverName, giverNameDict)

    def updateByName(self, name, data={}, delta={}):
        return self.updateById(self.getIdByName(name), data=data, delta=delta)
    """

    def printAll(self):
        print(self.elements)




p = Points('./chatlevel.json') # Points('./backups/test.json')

#p.addNew('test2', data={'n' : 'test2'})
if False:
    #print(p.updateById('test3', delta={'p' : 5}))
    #print(p.updateById('test2', delta={'p' : 5}))
    #print(p.updateById('test1', delta={'p' : 5}))
    p.transferPointsByIds('test3', {
        'test2' : 2,
        'test3' : 0
    })
    print(p.transferPointsByIdsSimple('test1', 'test2', 'all', partial=True))
#print(p.updateById('test1', delta={'p' : 15}))
#p.save()

# convert old data to new data, aka remove levels
if False:
    path = './chatlevel.json'
    try:
        elems = {}
        with open(path, 'r+') as file:
            elems = json.load(file)
        print(elems)
        for key in elems.keys():
            print(key)
            elem = elems[key]
            while elems[key]['l'] > 1:
                elems[key]['l'] -= 1
                elems[key]['p'] += p.getPointsForLevelUp(elems[key]['l'])
            del elems[key]['l']
        with open(path, 'w+') as file:
            json.dump(elems, file, indent=2)
            file.close()
    except:
        print('eh')
        pass




















