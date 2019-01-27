import transaction
import time
import persistent
import threading
import heapq
from modules.callbackitem import CallbackItem
from modules.get_logger import get_logger

logger = get_logger('callbackqueue')
state_lock = threading.RLock()  # necessary external lock...


class CallbackQueue(persistent.Persistent):
    """
    The queue containing the CallbackItems.
    Has to be wrapped by a CallbackQueueWorkerThread that works it, due to pickle limitations.
    """

    def __init__(self):
        super(CallbackQueue, self).__init__()
        self.items = []
        logger.info('Created new CallbackQueue')

    def print(self):
        with state_lock:
            logger.info('Callbackqueue has %i queued items' % len(self.items))

    def add(self, item: CallbackItem):
        with state_lock:
            heapq.heappush(self.items, item)
            self.save()
            logger.debug('Callbackqueue, added to queue, %d, %s'
                         % (len(self.items), ['%3.0f' % (i.time-time.time()) for i in self.items]))

    def pop(self):
        with state_lock:
            if len(self.items) == 0:
                return None
            item = heapq.heappop(self.items)
            self.save()
            transaction.commit()
            logger.debug('Callbackqueue, removed an item from queue, %d remaining' % len(self.items))
            return item

    def should_pop(self):
        with state_lock:
            if len(self.items) == 0:
                return False
            return self.items[0].ended()

    def save(self):
        with state_lock:
            transaction.begin()
            self._p_changed = True
            transaction.commit()


class CallbackQueueWorkerThread(threading.Thread):
    def __init__(self, queue: CallbackQueue):
        super(CallbackQueueWorkerThread, self).__init__()
        self.keep_running = True
        self.daemon = True
        self.queue = queue
        logger.info('Created new CallbackQueueWorkerThread')

    def stop(self):
        self.keep_running = False

    def run(self):
        while self.keep_running:
            while self.queue.should_pop():
                item = self.queue.pop()
                item.callback()
            time.sleep(0.5)


if __name__ == '__main__':
    q = CallbackQueue()
    w = CallbackQueueWorkerThread(q)
    import random
    for j in range(10):
        r = random.randint(0, 2+j)
        q.add(CallbackItem(r, int, r))
    w.start()
    w.join()
