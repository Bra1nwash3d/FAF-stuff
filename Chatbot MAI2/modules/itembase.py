import persistent.dict
import transaction
import json
from modules.callbackqueue import CallbackQueue
from modules.chatbase import Chatbase
from modules.effectbase import EffectBase
from modules.items.effectitem import EffectItem
from modules.items.market import Market
from modules.utils import get_logger, get_lock

logger = get_logger('itembase')
lock = get_lock('itembase')


class ItemBase(persistent.Persistent):
    """
    Loads item configuations from a json file, creates Item objects
    Also functions as market to buy items from
    """

    def __init__(self, queue: CallbackQueue, effectbase: EffectBase, chatbase: Chatbase):
        self.next_id = 0
        self.queue = queue
        self.effectbase = effectbase
        self.chatbase = chatbase
        self.items = persistent.dict.PersistentDict()
        self.markets = persistent.dict.PersistentDict()
        self.itemname_to_itemid = persistent.dict.PersistentDict()
        self.itemid_to_itemname = persistent.dict.PersistentDict()
        logger.info('Creating new ItemBase')

    def set(self, queue: CallbackQueue, effectbase: EffectBase, chatbase: Chatbase):
        self.queue = queue
        self.effectbase = effectbase
        self.chatbase = chatbase

    def reset(self):
        with lock:
            for market in self.markets.values():
                market.reset()
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

    def add_test_item(self, id_: str):
        with lock:
            item = self.test_item()
            logger.info(item.to_str())
            self.chatbase.get(id_).add_usable_item(item)

    def test_item(self) -> EffectItem:
        return self.get_item('test1')

    def get_available_markets(self, player_id: str, is_player_nick=True) -> [str]:
        with lock:
            markets = []
            entity = self.chatbase.get(player_id, is_nick=is_player_nick)
            for name, market in self.markets.items():
                if market.has_access(entity):
                    markets.append(name)
            return markets

    def get_market_items(self, market_id: str, player_id: str, is_player_nick=True) -> [str]:
        with lock:
            entity = self.chatbase.get(player_id, is_nick=is_player_nick)
            market = self.markets.get(market_id, None)
            if market is None:
                raise ValueError('Market "%s" does not exist!' % market_id)
            return market.get_item_list(entity)

    def update_items_list(self, json_path_items):
        with lock:
            try:
                with open(json_path_items, 'r+') as file:
                    effects = json.load(file)
                self.items.clear()
                self.itemname_to_itemid.clear()
                self.itemid_to_itemname.clear()
                self.items.update(effects)
                for k, v in self.items.items():
                    self.itemname_to_itemid[v.get('name')] = k
                    self.itemid_to_itemname[k] = v.get('name')
                for market in self.markets.values():
                    market.update(id_to_name=self.itemid_to_itemname)
                self.save()
                logger.info('ItemBase updated items from %s' % json_path_items)
            except Exception as e:
                logger.info(str(e))
                logger.warn('ItemBase failed updating items from %s' % json_path_items)

    def update_markets(self, json_path_markets):
        with lock:
            try:
                with open(json_path_markets, 'r+') as file:
                    markets_info = json.load(file)
                for market_config in markets_info.values():
                    self.__update_market(market_config)
                self.save()
                logger.info('ItemBase updated markets from %s' % json_path_markets)
            except Exception as e:
                logger.info(str(e))
                logger.warn('ItemBase failed updating markets from %s' % json_path_markets)

    def __update_market(self, market_config):
        with lock:
            name = market_config.get('name')
            if name in self.markets.keys():
                self.markets[name].update(**market_config, id_to_name=self.itemid_to_itemname)
            else:
                self.markets[name] = Market(self.queue, **market_config, id_to_name=self.itemid_to_itemname)
