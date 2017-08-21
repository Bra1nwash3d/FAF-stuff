import json
import threading
import time


class Events():
    def __init__(self, jsonpath):
        self.jsonpath = jsonpath
        self.events = {}
        self.lock = threading.Lock()
        try:
            with open(self.jsonpath, 'r+') as file:
                self.events = json.load(file)
        except:
            pass

    def save(self, path=False):
        self.lock.acquire()
        if not path:
            path = self.jsonpath
        with open(path, 'w+') as file:
            json.dump(self.events, file, indent=2)
            file.close()
        self.lock.release()

    def getFilePath(self):
        return self.jsonpath

    def reset(self):
        self.lock.acquire()
        self.events = {}
        self.lock.release()

    def addEvent(self, key, data):
        self.lock.acquire()
        if not self.events.get(key, False):
            self.events[key] = []
        data['t'] = time.time()
        self.events[key].append(data)
        self.lock.release()

    def getData(self, key):
        return self.events.get(key, [])