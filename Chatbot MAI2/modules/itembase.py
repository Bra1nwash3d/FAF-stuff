import persistent.dict
import transaction
import json
from modules.callbackqueue import CallbackQueue
from modules.chatbase import Chatbase
from modules.effectbase import EffectBase
from modules.items.effectitem import EffectItem
from modules.utils import get_logger, get_lock

logger = get_logger('itembase')
lock = get_lock('itembase')


class ItemBase(persistent.Persistent):
    """
    Loads item configuations from a json file, creates Item objects
    Also functions as market to buy items from
    """

    def __init__(self, queue: CallbackQueue, effectbase: EffectBase, chatbase: Chatbase, json_path=None):
        self.json_path = json_path
        self.next_id = 0
        self.queue = queue
        self.effectbase = effectbase
        self.chatbase = chatbase
        self.items = persistent.dict.PersistentDict()
        self.itemname_to_itemid = persistent.dict.PersistentDict()
        self.update_items_list(self.json_path)
        logger.info('Creating new ItemBase')

    def set(self, queue: CallbackQueue, effectbase: EffectBase, chatbase: Chatbase):
        self.queue = queue
        self.effectbase = effectbase
        self.chatbase = chatbase

    def reset(self):
        with lock:
            # actually nothing to be done, as effects are in the queue
            self.save()
            logger.info('Reset ItemBase')

    def migrate(self):
        """ to migrate the db when new class elements are added - call self.save() if you do """
        with lock:
            # self.x = self.__dict__.get('x', 'oh a new self.x!')
            pass

    def print(self):
        with lock:
            logger.info('ItemBase has {n} items loaded'.format(**{
                'n': len(self.items),
            }))

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

    def get_item(self, id_, is_name=False):
        """ returns an Effect object of effect with given id, otherwise None """
        with lock:
            if is_name:
                id_ = self.itemname_to_itemid.get(id_)
            cfg = self.items.get(id_)
            if cfg is None:
                return None
            if cfg.get('type') == 'effectitem':
                effect = self.effectbase.get_effect(cfg.get('effect'))
                return EffectItem(self.__next_id(), id_, cfg.get('name'), cfg.get('description'), effect,
                                  cfg.get('visible'), cfg.get('uses'))
            return None

    def add_item(self, player_id: str, item_id: str, is_player_nick=True, is_item_name=False) -> str:
        with lock:
            item = self.get_item(item_id, is_name=is_item_name)
            if item is None:
                return 'Failed creating item! Id does probably not exist...'
            self.chatbase.get(player_id, is_nick=is_player_nick).add_usable_item(item)
            return 'Gave item %s to %s' % (item.item_id, player_id)
        pass

    def add_test_item(self, id_: str):
        with lock:
            item = self.test_item()
            logger.info(item.to_str())
            self.chatbase.get(id_).add_usable_item(item)
        pass

    def test_item(self):
        return self.get_item('test1')

    def update_items_list(self, json_path=None):
        with lock:
            self.json_path = json_path if json_path is not None else self.json_path
            try:
                with open(self.json_path, 'r+') as file:
                    effects = json.load(file)
                self.items.clear()
                self.itemname_to_itemid.clear()
                self.items.update(effects)
                for k, v in self.items.items():
                    self.itemname_to_itemid[v.get('name')] = k
                self.save()
                logger.info('ItemBase updated from %s' % self.json_path)
            except Exception as e:
                logger.info(str(e))
                logger.info('ItemBase failed updating from %s' % self.json_path)
