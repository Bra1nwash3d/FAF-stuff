import persistent.dict
import transaction
from modules.chatentity import ChatEntity
from modules.callbackqueue import CallbackQueue
from modules.callbackitem import CallbackItem
from modules.distributions import sample
from modules.utils import get_logger, get_lock

logger = get_logger('market')
lock = get_lock('market')


class Market(persistent.Persistent):
    """
    A market to buy items from
    """

    def __init__(self, queue: CallbackQueue, name: str=None, description: str=None,
                 items_config: dict=None, requirements: dict=None, id_to_name: dict=None):
        self.queue = queue
        self.name = None
        self.description = None
        self.items_config = None                            # info how often they stock up etc
        self.requirements = None                            # who can access the market
        self.id_to_name = None
        self.update(name, description, items_config, requirements, id_to_name)
        self.stock = persistent.dict.PersistentDict()       # currently available items
        self.set_stocks_init()
        self.start_refills()
        logger.info('Creating new Market: %s' % self.name)

    def update(self, name: str=None, description: str=None, items_config: dict=None,
               requirements: dict=None, id_to_name: dict=None):
        with lock:
            self.name = name if name is not None else self.name
            self.description = description if description is not None else self.description
            self.requirements = requirements if requirements is not None else self.requirements
            self.items_config = items_config if items_config is not None else self.items_config
            self.id_to_name = id_to_name if id_to_name is not None else self.id_to_name

    def reset(self):
        with lock:
            self.set_stocks_init()
            self.save()
            self.start_refills()
            logger.info('Reset Market %s' % self.name)

    def migrate(self):
        """ to migrate the db when new class elements are added - call self.save() if you do """
        with lock:
            # self.x = self.__dict__.get('x', 'oh a new self.x!')
            pass

    def print(self):
        with lock:
            logger.info('Market {name} has {n} items in stock'.format(**{
                'name': self.name,
                'n': sum([v for v in self.stock.values()]),
            }))

    def save(self):
        with lock:
            self._p_changed = True
            transaction.commit()

    def set_stocks_init(self):
        with lock:
            logger.info('Market %s resetting stocks' % self.name)
            self.stock.clear()
            for id_, v in self.items_config.items():
                self.stock[id_] = v.get('init_stock')

    def start_refills(self):
        with lock:
            for id_, cfg in self.items_config.items():
                duration = sample(**cfg.get('refill'))
                self.queue.add(CallbackItem(duration, self.on_refill, item_id=id_, count=1))

    def on_refill(self, item_id=None, count=1):
        with lock:
            cfg = self.items_config.get(item_id, None)
            if cfg is not None:
                self.stock[item_id] = min([self.stock.get(item_id) + count, cfg.get('max_stock')])
                duration = sample(**cfg.get('refill'))
                logger.info('market %s, refilling %s to %d (by %d), next one in %.2f'
                            % (self.name, item_id, self.stock[item_id], count, duration))
                self.save()
                self.queue.add(CallbackItem(duration, self.on_refill, item_id=item_id, count=1))

    def get_stock(self) -> dict:
        return self.stock

    def has_access(self, _: ChatEntity):
        with lock:
            # TODO requirements
            return True

    def get_item_list(self, entity: ChatEntity) -> [str]:
        with lock:
            if not self.has_access(entity):
                raise ValueError('%s does not have access to the %s market!' % (entity.nick, self.name))
            items = []
            for item_id, count in self.stock.items():
                items.append('{name}: {p} points, {n} in stock'.format(**{
                    'name': self.id_to_name.get(item_id, '?'),
                    'p': self.items_config.get(item_id).get('cost'),
                    'n': count,
                }))
            return items
