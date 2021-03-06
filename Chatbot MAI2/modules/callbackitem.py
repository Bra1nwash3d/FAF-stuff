import transaction
import time
import persistent
import functools
from modules.utils import get_logger

logger = get_logger('callbackitem')


@functools.total_ordering
class CallbackItem(persistent.Persistent):
    """ A class for delayed function executing """

    def __init__(self, seconds, fun, *args, **kwargs):
        super(CallbackItem, self).__init__()
        logger.info('cbitem args: %s' % str(args))
        self.time = seconds + time.time()
        self.fun = fun
        self.args = args
        self.kwargs = kwargs
        self.done = False
        self.save()
        logger.debug('created CallbackItem, %ss, %s, %s' % (seconds, args, kwargs))

    def callback(self):
        if self.done:
            return None
        r = self.fun(*self.args, **self.kwargs)
        self.done = True
        transaction.commit()
        self.save()
        logger.debug('using CallbackItem, %s, %s' % (self.args, self.kwargs))
        return r

    def save(self):
        self._p_changed = True
        transaction.commit()

    def rem_time(self) -> float:
        return self.time - time.time()

    def ended(self) -> bool:
        return self.time <= time.time()

    def __eq__(self, other):
        return self.time == other.time

    def __lt__(self, other):
        return self.time < other.time


if __name__ == '__main__':
    c1 = CallbackItem(10, int, '4')
    c2 = CallbackItem(15, int, '12')
    logger.info(c1 < c2)
    logger.info(c1 > c2)
    logger.info(c1 == c2)
    logger.info(c1 <= c2)
    logger.info(c1.callback())
    logger.info(c1.callback())
    logger.info(c2.callback())
