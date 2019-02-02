import persistent
import persistent.dict
import transaction
import time
import functools
from modules.types import PointType
from modules.callbackitem import CallbackItem
from modules.callbackqueue import CallbackQueue
from modules.utils import get_logger, time_to_str

logger = get_logger('effects')


@functools.total_ordering
class PointsEffect(persistent.Persistent):
    """ An effect, given to a ChatEntity, which calls the begin method. """

    def __init__(self, id_, name, duration: int, queue: CallbackQueue, group='not_set', adds=None, mults=None):
        super(PointsEffect, self).__init__()
        self.id = id_
        self.name = name
        self.duration = duration
        self.queue = queue
        self.time = None
        self.adds = persistent.dict.PersistentDict()   # will stack additively, then multiplied with base
        self.mults = persistent.dict.PersistentDict()  # will be multiplied with each other and base
        self.group = group
        if adds is not None:
            self.adds.update(adds)
        if mults is not None:
            self.mults.update(mults)
        self.save()

    def migrate(self):
        """ to migrate the db when new class elements are added - call self.save() if you do """
        # self.x = self.__dict__.get('x', 'oh a new self.x!')
        pass

    def add_add(self, type_: PointType, add: float):
        self.adds[type_] = self.adds.get(type_, 0) + add
        self.save()

    def get_adds(self) -> dict:
        return self.adds

    def add_mult(self, type_: PointType, mult: float):
        self.mults[type_] = self.mults.get(type_, 1) * mult
        self.save()

    def get_mults(self) -> dict:
        return self.mults

    def begin(self, fun, *args, **kwargs):
        """ queues the effect for expiration, then calls fun """
        self.queue.add(CallbackItem(self.duration, fun, *args, **kwargs))
        self.time = time.time() + self.duration
        self.save()

    def save(self):
        self._p_changed = True
        transaction.commit()

    def rem_time(self) -> float:
        return self.time - time.time()

    def is_expired(self) -> bool:
        # really annoying to not be able to use the callbackitem for this
        # but somehow the reference to it is set to None once given to the queue
        if self.time is None:
            return False
        return self.rem_time() < 0

    def affects_str(self) -> str:
        affects = []
        if len(self.adds) > 0:
            affects.append(', '.join(['%s by +%.2f' % (PointType.as_str(k), v) for k, v in self.adds.items()]))
        if len(self.mults) > 0:
            affects.append(', '.join(['%s by x%.2f' % (PointType.as_str(k), v) for k, v in self.mults.items()]))
        return ', '.join(affects)

    def to_str(self):
        """ used for listing effects in chat """
        rem_time = self.rem_time()
        return '{name}: affects [{effects}], {t}'.format(**{
            'name': self.name,
            'effects': self.affects_str(),
            't': 'expires in %s' % time_to_str(self.time - time.time()) if rem_time > 0 else 'expired',
        })

    def __str__(self):
        return '%s: id:%d, dur:%d, mults:%s' % (self.__class__.__name__, self.duration, self.id, self.mults)

    def __eq__(self, other):
        # not considering that they may have effects on different point types - those should not stack though
        for k, v in self.mults.items():
            if v != other.mults.get(k, -1):
                return False
        for k, v in self.adds.items():
            if v != other.adds.get(k, -1):
                return False
        return True

    def __lt__(self, other):
        # not considering that they may have effects on different point types - those should not stack though
        for k, v in self.mults.items():
            if v < other.mults.get(k, -1):
                return True
        for k, v in self.adds.items():
            if v < other.adds.get(k, -1):
                return True
        return False
