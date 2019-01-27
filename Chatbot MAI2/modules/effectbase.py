import persistent.dict
import transaction
from modules.effects import PointsEffect
from modules.types import *
from modules.callbackqueue import CallbackQueue
from modules.get_logger import get_logger

logger = get_logger('effectbase')


class EffectBase(persistent.Persistent):
    def __init__(self, queue: CallbackQueue, json_path=None):
        self.json_path = None
        self.next_id = 0
        self.update_effects_list(json_path)
        self.queue = queue
        self.effects = persistent.dict.PersistentDict()
        logger.info('Creating new EffectBase')

    def __next_id(self):
        id_ = self.next_id
        self.next_id += 1
        self.save()
        return id_

    def save(self):
        self._p_changed = True
        transaction.commit()

    def update_effects_list(self, json_path):
        self.json_path = json_path
        logger.info('EffectBase updating from %s' % json_path)
        # TODO read file, add effects to some list, ...

    def print(self):
        logger.info('EffectBase has {n} effects loaded'.format(**{
            'n': len(self.effects),
        }))

    def test_effect(self):
        return PointsEffect(self.__next_id(), name='testeffect', queue=self.queue, duration=30, default={
            PointType.CHAT: 2.0,
        })
