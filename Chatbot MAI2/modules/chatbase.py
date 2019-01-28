import BTrees.OOBTree
import persistent.dict
import transaction
import time
from heapq import nlargest, nsmallest
from modules.utils import get_logger, not_pinging_name, get_lock, time_to_str
from modules.chatentity import ChatEntity
from modules.callbackqueue import CallbackQueue
from modules.callbackitem import CallbackItem
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
        self.ignored_players = persistent.dict.PersistentDict()  # these can not get points from chatting
        self.eventbase = eventbase
        self.effectbase = effectbase
        self.spam_protect = spam_protect
        self.queue = queue

        # misc vars
        self.points_cost_on_kick = 0
        self.points_cost_on_ban = 0

        self.save()
        logger.info('Created new Chatbase')

    def reset(self):
        with lock:
            self.entities.clear()
            self.save()
            logger.info('Reset Chatbase')

    def update_vars(self, points_cost_on_kick=None, points_cost_on_ban=None, **_):
        with lock:
            # function to set misc vars
            self.points_cost_on_kick =\
                points_cost_on_kick if points_cost_on_kick is not None else self.points_cost_on_kick
            self.points_cost_on_ban = points_cost_on_ban if points_cost_on_ban is not None else self.points_cost_on_ban
            self.save()
            logger.info('Chatbase, updating kick:%d, ban:%d' % (points_cost_on_kick, points_cost_on_ban))

    def save(self):
        with lock:
            self._p_changed = True
            transaction.commit()

    def add(self, id_: str, nick: str):
        with lock:
            e = self.get(id_)
            e.nick = nick

    def get(self, id_: str, is_nick=False) -> ChatEntity:
        """ get an entity of id, create if not existing """
        with lock:
            id_ = id_ if not is_nick else self.nick_to_id.get(id_, id_)
            if id_ not in self.entities:
                self.entities[id_] = ChatEntity(id_)
            return self.entities[id_]

    def get_id(self, nick: str):
        """ get id of a nick, with abuse protection """
        with lock:
            if len(nick) < 3:
                return None
            return self.nick_to_id.get(nick, None)

    def get_k(self, k=5, largest=True, incl_players=True, incl_channels=True, point_type: PointType=None):
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

    def get_k_points_str(self, point_type: PointType=None, **kwargs) -> str:
        with lock:
            if point_type is None:
                # special text for point sum, as we can use levels
                return ', '.join(['%s (level %d)' % (not_pinging_name(e.nick), e.get_level())
                                  for e in self.get_k(**kwargs, point_type=point_type)])
            return ', '.join(['%s (%d points)' % (not_pinging_name(e.nick), e.get_points(point_type))
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

    def on_chat(self, msg, player_id: str, player_nick=None, channel_id=None):
        with lock:
            if self.ignored_players.get(player_id, True):
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
            return '%s received effect: [%s]' % (entity.nick, effect.to_str())

    def add_to_ignore(self, id_: str, is_nick=False, duration=None) -> str:
        with lock:
            id_ = id_ if not is_nick else self.nick_to_id.get(id_, id_)
            if id_ is None:
                return 'Failed adding %s to the ignore list! The player id was not found in the DB!' % id_
            if id_ in self.ignored_players.keys():
                return '%s is already on the ignore list!' % id_
            self.ignored_players[id_] = (duration + time.time()) if duration is not None else duration
            self.save()
            if duration is not None:
                self.queue.add(CallbackItem(duration, self.remove_from_ignore, id_))
                return 'Added %s to the ignore list, will be removed in %s' % (id_, time_to_str(duration))
            return 'Added %s to the ignore list!' % id_

    def get_ignore_list(self) -> str:
        with lock:
            items = []
            for id_, d in self.ignored_players.items():
                part = '{n}' if d is None else '{n} ({d})'
                items.append(part.format(**{'n': self.get(id_).nick, 'd': time_to_str(d - time.time())}))
            return 'Ignored players: %s' % ', '.join(items)

    def remove_from_ignore(self, id_: str, is_nick=False) -> str:
        with lock:
            id_ = id_ if not is_nick else self.nick_to_id.get(id_, id_)
            if id_ is None:
                return 'Failed removing %s from the ignore list! The player id was not found in the DB!' % id_
            if self.ignored_players.get(id_, False) is False:
                return '%s is not on the ignore list!' % id_
            self.ignored_players.pop(id_)
            self.save()
            return 'Removed %s from the ignore list!' % id_
