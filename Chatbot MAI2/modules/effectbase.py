import persistent.dict
import transaction
import json
from modules.effects import PointsEffect
from modules.types import *
from modules.callbackqueue import CallbackQueue
from modules.utils import get_logger, get_lock

logger = get_logger('effectbase')
lock = get_lock('effectbase')


class EffectBase(persistent.Persistent):
    def __init__(self, queue: CallbackQueue, json_path=None):
        self.json_path = None
        self.next_id = 0
        self.update_effects_list(json_path)
        self.queue = queue
        self.effects = persistent.dict.PersistentDict()
        logger.info('Creating new EffectBase')

    def __next_id(self):
        with lock:
            id_ = self.next_id
            self.next_id += 1
            self.save()
            return id_

    def save(self):
        with lock:
            self._p_changed = True
            transaction.commit()

    def update_effects_list(self, json_path=None):
        with lock:
            self.json_path = json_path if json_path is not None else self.json_path
            try:
                with open(self.json_path, 'r+') as file:
                    effects = json.load(file)
                self.effects.clear()
                self.effects.update(effects)
                logger.info('EffectBase updated from %s' % self.json_path)
            except Exception as e:
                logger.info(str(e))
                logger.info('EffectBase failed updating from %s' % self.json_path)
            logger.info(self.effects)

    def print(self):
        with lock:
            logger.info('EffectBase has {n} effects loaded'.format(**{
                'n': len(self.effects),
            }))

    def test_effect(self):
        with lock:
            return PointsEffect(self.__next_id(), name='testeffect', queue=self.queue, duration=30, default={
                PointType.CHAT: 2.0,
            })
