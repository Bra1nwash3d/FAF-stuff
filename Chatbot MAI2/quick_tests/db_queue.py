from modules.callbackitem import CallbackItem
from modules.callbackqueue import CallbackQueue, CallbackQueueWorkerThread
import ZODB
import ZODB.FileStorage
import os
import time
import random


class X:
    def __init__(self):
        db_path = './data/data.fs'
        os.makedirs('/'.join([p for p in db_path.split('/')[:-1]]), exist_ok=True)
        storage = ZODB.FileStorage.FileStorage(db_path)
        self.db = ZODB.DB(storage)
        self.db_con = self.db.open()
        self.db_root = self.db_con.root
        try:
            self.db_root.callbackqueue.print()
        except:
            self.db_root.callbackqueue = CallbackQueue()
            self.db_root.callbackqueue.print()
        self.worker = CallbackQueueWorkerThread(self.db_root.callbackqueue)
        self.worker.start()

    def stop(self):
        self.worker.stop()

    def insert_random(self, n, t0, t1):
        for i in range(n):
            tr = random.randint(t0, t1)
            self.db_root.callbackqueue.add(CallbackItem(tr, int, '32'))

    def print(self):
        self.db_root.callbackqueue.print()


if __name__ == '__main__':
    x = X()
    x.insert_random(2, 10, 20)
    x.print()
    for j in range(10):
        time.sleep(0.5)
        print('.')
    x.stop()
    x.print()

