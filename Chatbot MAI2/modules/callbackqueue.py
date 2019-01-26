import transaction
import time
import persistent
import threading
import heapq
from modules.callbackitem import CallbackItem
from modules.get_logger import get_logger

logger = get_logger('callbackqueue')


class CallbackQueue(persistent.Persistent, threading.Thread):
    def __init__(self):
        super(CallbackQueue, self).__init__()
        self.items = []
        self.keep_running = True
        self.daemon = True
        logger.info('Created new CallbackQueue')

    def add(self, item: CallbackItem):
        heapq.heappush(self.items, item)
        logger.info('----- %d' % len(self.items))
        logger.info(['%3.0f' % i.time for i in self.items])

    def stop(self):
        self.keep_running = False

    def run(self):
        while self.keep_running:
            while True:
                if len(self.items) == 0:
                    break
                if self.items[0].time > time.time():
                    break
                item = heapq.heappop(self.items)
                item.callback()
            time.sleep(0.5)


if __name__ == '__main__':
    q = CallbackQueue()
    import random
    for i in range(10):
        r = random.randint(0, 2+i)
        q.add(CallbackItem(r, int, r))
    q.start()
    q.join()
