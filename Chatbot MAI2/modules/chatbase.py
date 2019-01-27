import BTrees.OOBTree
import persistent.list
import transaction
from heapq import nlargest, nsmallest
from modules.utils import get_logger, not_pinging_name, get_lock
from modules.chatentity import ChatEntity
from modules.callbackqueue import CallbackQueue
from modules.eventbase import Eventbase
from modules.timer import SpamProtect
from modules.types import PointType
from modules.effectbase import EffectBase

logger = get_logger('chatbase')
lock = get_lock('chatbase')


class Chatbase(persistent.Persistent):
    def __init__(self, eventbase: Eventbase, spam_protect: SpamProtect, queue: CallbackQueue, effectbase: EffectBase):
        super(Chatbase, self).__init__()
        self.entities = BTrees.OOBTree.BTree()
        self.nick_to_id = BTrees.OOBTree.BTree()
        self.eventbase = eventbase
        self.effectbase = effectbase
        self.spam_protect = spam_protect
        self.queue = queue

        # misc vars
        self.points_cost_on_kick = 0
        self.points_cost_on_ban = 0

        # TODO make points some adjustable variable, stored in VARS i guess
        self.save()
        logger.info('Created new Chatbase')

    def update_vars(self, points_cost_on_kick=None, points_cost_on_ban=None, **_):
        with lock:
            # function to set misc vars
            self.points_cost_on_kick =\
                points_cost_on_kick if points_cost_on_kick is not None  else self.points_cost_on_kick
            self.points_cost_on_ban = points_cost_on_ban if points_cost_on_ban is not None else self.points_cost_on_ban
            self.save()
            logger.info('Chatbase, updating kick:%d, ban:%d' % (points_cost_on_kick, points_cost_on_ban))

    def save(self):
        with lock:
            self._p_changed = True
            transaction.commit()

    def add(self, id_, nick):
        with lock:
            e = self.get(id_)
            e.nick = nick

    def get(self, id_, is_nick=False) -> ChatEntity:
        """ get an entity of id, create if not existing """
        with lock:
            id_ = id_ if not is_nick else self.nick_to_id.get(id_, id_)
            if id_ not in self.entities:
                self.entities[id_] = ChatEntity(id_)
            return self.entities[id_]

    def get_id(self, nick):
        """ get id of a nick, with abuse protection """
        with lock:
            if len(nick) < 3:
                return None
            return self.nick_to_id.get(nick, None)

    def get_k(self, k=5, largest=True, incl_players=True, incl_channels=True, point_type=None):
        """ get k of a group, filtered by """
        with lock:
            fun, default = (nlargest, -999999999) if largest else (nsmallest, 99999999999)

            def _cond(e):
                if e is None:
                    return False
                if e.id is None:
                    return False
                return e.is_player == incl_players or e.is_channel == incl_channels

            return fun(k, self.entities.values(), key=lambda e: e.get_points(point_type) if _cond(e) else default)

    def get_k_points_str(self, point_type=None, **kwargs) -> str:
        with lock:
            return ', '.join(['(%s, %d)' % (not_pinging_name(e.nick), e.get_points(point_type))
                              for e in self.get_k(**kwargs, point_type=point_type)])

    def get_k_most_points_str(self, **kwargs) -> str:
        with lock:
            kwargs['largest'] = True
            return 'Most points: %s' % self.get_k_points_str(**kwargs)

    def print(self):
        with lock:
            logger.info('Chatbase has {n} entities'.format(**{
                'n': len(self.entities),
            }))

    def str_to_points(self, str_: str) -> int:
        # TODO not static yet because there will be boost words etc later
        return len(str_)

    def __generic_on_something(self, points, player_id, point_type: PointType, player_nick=None, channel_id=None,
                               partial=True):
        """ generic function, adds points of type to channel and gets channel mult if available,
            then adds modified points to player and updates nick
        """
        with lock:
            chat_mult = 1
            if channel_id is not None:
                self.get(channel_id).update_points(points, channel_id, type_=point_type, partial=partial)
                chat_mult = self.get(channel_id).get_mult(type_=point_type)
                self.nick_to_id[channel_id] = channel_id
            self.get(player_id).update_points(points*chat_mult, player_nick, type_=point_type, partial=partial)
            self.nick_to_id[player_nick] = player_id

    def on_chat(self, msg, player_id, player_nick=None, channel_id=None):
        with lock:
            chat_mult, points = 1, self.str_to_points(msg)
            self.__generic_on_something(points, player_id, PointType.CHAT, player_nick, channel_id)

    def on_kick(self, by: str, target: str, channel: str, msg: str):
        with lock:
            id1, id2, cid = self.get_id(by), self.get_id(target), self.get_id(channel)
            msg_add = ''
            if id1 is None or id2 is None:
                msg_add = ', but one of them is not in the DB (%s, %s)' % (id1, id2)
            else:
                logger.info('kick!!!! %d' % self.points_cost_on_kick)
                self.__generic_on_something(self.points_cost_on_kick, id2, PointType.KICK, partial=True)
                self.eventbase.add_on_kick_event(id1, id2, channel, msg, self.points_cost_on_kick)
            logger.info('{kicktarget} got kicked from {channel} by {nick} with msg "{msg}"{msgadd}!'.format(**{
                'kicktarget': target,
                'channel': channel,
                'nick': by,
                'msg': msg,
                'msgadd': msg_add
            }))

    def transfer_points(self, id1, id2, amount: int, type1: PointType, type2: PointType=None, partial=False) -> int:
        """ transfer points from A to B, affected by multipliers of A but not B (sum remains the same) """
        with lock:
            if amount <= 0:
                return 0
            type2 = type2 if type2 is not None else type1
            p, _ = self.get(id1).update_points(-amount, nick=None, type_=type1, partial=partial)
            self.get(id2).update_points(-p, nick=None, type_=type2, mult_enabled=False)
            logger.debug('transfer %d/%d, partial %s' % (amount, p, partial))
            return -p

    def tip(self, nick1, nick2, amount: int, partial=True) -> (int, str):
        """ chattip, nick1 tips amount points to nick2 """
        with lock:
            id1, id2 = self.get_id(nick1), self.get_id(nick2)
            if id1 is None or id2 is None:
                logger.debug('failed tipping: (%s, %s) -> (%s, %s)' % (nick1, id1, nick2, id2))
                return 0, 'Failed tipping, target is not listed in the DB.'
            p = self.transfer_points(id1, id2, amount, type1=PointType.CHATTIP, partial=partial)
            # self.transfer_points(id1, id2, p, type1=PointType.CHAT)
            logger.debug('tipped %d: (%s, %s) -> (%s, %s)' % (p, nick1, id1, nick2, id2))
            self.eventbase.add_chat_tip_event(id1, id2, amount, p)
            return p, '%s tipped %d points to %s!' % (nick1, p, nick2)

    def apply_test_effect(self, id_):
        """ Applies a test effect to a chatentity """
        with lock:
            self.get(id_).add_effect(self.effectbase.test_effect())

    def apply_effect(self, entity_id: str, effect_id: str, is_player_nick=False, is_effect_name=False) -> str:
        """ Applies an effect to a chatentity """
        with lock:
            effect = self.effectbase.get_effect(effect_id, is_name=is_effect_name)
            entity = self.get(entity_id, is_nick=is_player_nick)
            if effect is None:
                return 'Failed applying the effect to %s! It was probably not found...' % entity.nick
            entity.add_effect(effect)
            return '%s received effect: %s' % (entity.nick, effect.to_str())
