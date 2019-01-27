import persistent
import persistent.dict
import transaction
import time
from modules.types import PointType
from modules.callbackitem import CallbackItem
from modules.callbackqueue import CallbackQueue
from modules.utils import get_logger, time_to_str

logger = get_logger('effects')


class PointsEffect(persistent.Persistent):

    def __init__(self, id_, name, duration: int, queue: CallbackQueue, default=None):
        super(PointsEffect, self).__init__()
        self.id = id_
        self.name = name
        self.duration = duration
        self.queue = queue
        self.time = None
        self.mults = persistent.dict.PersistentDict()
        if default is not None:
            self.mults.update(default)
        self.save()

    def add_mult(self, type_: PointType, mult: float):
        self.mults[type_] = self.mults.get(type_, 1) * mult
        self.save()

    def get_mults(self) -> dict:
        return self.mults

    def begin(self, entity):
        """ entity has to have a function update_effects, but importing ChatEntity would be circular """
        self.queue.add(CallbackItem(self.duration, entity.update_effects))
        self.time = time.time() + self.duration
        self.save()

    def save(self):
        self._p_changed = True
        transaction.commit()

    def is_expired(self) -> bool:
        # really annoying to not be able to use the callbackitem for this
        # but somehow the reference to it is set to None once given to the queue
        return self.time <= time.time()

    def to_str(self):
        """ used for listing effects in chat """
        return '{name}: affects [{effects}], expires in {t}'.format(**{
            'name': self.name,
            'effects': ', '.join(['%s by x%.1f' % (PointType.as_str(k), v) for k, v in self.mults.items()]),
            't': time_to_str(self.time - time.time())
        })

    def __str__(self):
        return '%s: id:%d, dur:%d, mults:%s' % (self.__class__.__name__, self.duration, self.id, self.mults)
