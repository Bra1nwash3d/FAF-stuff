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
    """
    Loads effect configuations from a json file, creates Effect objects
    """

    def __init__(self, queue: CallbackQueue, json_path=None):
        self.json_path = json_path
        self.next_id = 0
        self.queue = queue
        self.effects = persistent.dict.PersistentDict()
        self.effectname_to_effectid = persistent.dict.PersistentDict()
        self.update_effects_list(self.json_path)
        logger.info('Creating new EffectBase')

    def set(self, queue: CallbackQueue):
        self.queue = queue

    def reset(self):
        with lock:
            # actually nothing to be done, as effects are in the queue
            self.save()
            logger.info('Reset EffectBase')

    def migrate(self):
        """ to migrate the db when new class elements are added - call self.save() if you do """
        with lock:
            # self.x = self.__dict__.get('x', 'oh a new self.x!')
            pass

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
                self.effectname_to_effectid.clear()
                self.effects.update(effects)
                for k, v in self.effects.items():
                    self.effectname_to_effectid[v.get('name')] = k
                self.save()
                logger.info('EffectBase updated from %s' % self.json_path)
            except Exception as e:
                logger.info(str(e))
                logger.info('EffectBase failed updating from %s' % self.json_path)

    def print(self):
        with lock:
            logger.info('EffectBase has {n} effects loaded'.format(**{
                'n': len(self.effects),
            }))

    def get_effect(self, id_, is_name=False):
        """ returns an Effect object of effect with given id, otherwise None """
        with lock:
            if is_name:
                id_ = self.effectname_to_effectid.get(id_)
            cfg = self.effects.get(id_)
            if cfg is None:
                return None
            pt_add = {PointType.from_str(k): v for k, v in cfg.get('increases').items()}
            pt_mult = {PointType.from_str(k): v for k, v in cfg.get('multipliers').items()}
            logger.debug('EffectBase geteffect for %s, pt_mult: %s' % (id_, str(pt_mult)))
            return PointsEffect(self.__next_id(), name=cfg.get('name'), queue=self.queue, duration=cfg.get('duration'),
                                adds=pt_add, mults=pt_mult, group=cfg.get('group', 'unknown'))

    def test_effect(self):
        with lock:
            return PointsEffect(self.__next_id(), name='test1', queue=self.queue, duration=30, mults={
                PointType.CHAT: 2.0,
            })

    @staticmethod
    def get_updated_effects(effects: list) -> (list, list):
        # clear effects that have run out
        j = 0
        while j < len(effects):
            e = effects[j]
            if e.is_expired():
                effects.pop(j)
            else:
                j += 1
        # group remaining effects into groups, effects within groups can not stack
        groups = {}
        for e in effects:
            if groups.get(e.group, None) is None:
                groups[e.group] = []
            groups[e.group].append(e)
        # select strongest effect of each group
        to_apply = []
        for g in groups.values():
            to_apply.append(max(g))
        return effects, to_apply
