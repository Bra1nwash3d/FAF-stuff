import BTrees.OOBTree
import persistent.dict
import transaction
import time
from heapq import nlargest, nsmallest
from modules.utils import get_logger, not_pinging_name, get_lock, time_to_str
from modules.utils import get_msg_fun as gmf
from modules.chatentity import ChatEntity
from modules.callbackqueue import CallbackQueue
from modules.callbackitem import CallbackItem
from modules.eventbase import Eventbase
from modules.timer import SpamProtect
from modules.types import PointType, ChatType
from modules.effectbase import EffectBase
from modules.itembase import ItemBase

logger = get_logger('chatbase')
lock = get_lock('chatbase')


class Chatbase(persistent.Persistent):
    def __init__(self, eventbase: Eventbase, spam_protect: SpamProtect, queue: CallbackQueue,
                 effectbase: EffectBase, itembase: ItemBase):
        super(Chatbase, self).__init__()
        self.entities = BTrees.OOBTree.BTree()
        self.nick_to_id = persistent.dict.PersistentDict()
        self.ignored_players = persistent.dict.PersistentDict()  # these can not get points from chatting
        self.chat_channels = persistent.dict.PersistentDict()    # in these one can get points from chatting
        self.game_channels = persistent.dict.PersistentDict()    # in these one can play chat games
        self.join_messages = persistent.dict.PersistentDict()    # {name: msg} when special users join channels
        self.eventbase = eventbase
        self.effectbase = effectbase
        self.itembase = itembase
        self.spam_protect = spam_protect
        self.queue = queue

        # misc vars
        self.points_cost_on_kick = 0
        self.points_cost_on_ban = 0

        self.save()
        logger.info('Created new Chatbase')

    def set(self, eventbase: Eventbase, spam_protect: SpamProtect, queue: CallbackQueue,
            effectbase: EffectBase, itembase: ItemBase):
        self.eventbase = eventbase
        self.effectbase = effectbase
        self.spam_protect = spam_protect
        self.itembase = itembase
        self.queue = queue

    def reset(self):
        with lock:
            self.entities.clear()
            self.save()
            logger.info('Reset Chatbase')

    def migrate(self):
        """ to migrate the db when new class elements are added - call self.save() if you do """
        with lock:
            # self.x = self.__dict__.get('x', 'oh a new self.x!')
            # migrate all chatentities
            for ce in self.entities.itervalues():
                ce.migrate()

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

    def get_k(self, k=5, largest=True, incl_players=True, incl_channels=True, point_type: PointType=None) -> list:
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
            entities = self.get_k(**kwargs, point_type=point_type)
            self.__update_rankings(entities, **kwargs, point_type=point_type)
            if point_type is None:
                # special text for point sum, as we can use levels
                return ', '.join(['%s (level %d)' % (not_pinging_name(e.nick), e.get_level()) for e in entities])
            return ', '.join(['%s (%d points)'
                              % (not_pinging_name(e.nick), e.get_points(point_type)) for e in entities])

    def __update_rankings(self, entities: [ChatEntity], largest=True, incl_players=True, incl_channels=True,
                          point_type: PointType=None):
        """ updates on_join strings for players """
        # to extend for more point types, probably best to store top players in new dict {pointtype: {name, ranking}}
        # and update that, then renew all on_join strings

        # top chatwarriors
        if incl_players and not incl_channels and largest:
            # point sum
            if point_type is None:
                self.join_messages.clear()
                for i, e in enumerate(entities):
                    self.join_messages[e.id] =\
                        'Behold! {name}, currently rank %d on the chatlvl ladder, has joined this chat!' % (i+1)
                    if i >= 4:
                        break
                self.save()

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

    def on_chat(self, msg: str, player_id: str, player_nick=None, channel_id=None):
        with lock:
            if channel_id not in self.chat_channels:
                return
            if player_id in self.ignored_players:
                return
            chat_mult, points = 1, self.str_to_points(msg)
            self.__generic_on_something(points, player_id, PointType.CHAT, player_nick, channel_id)

    def on_join(self, medium: ChatType, player_id: str, player_nick, channel_id=None):
        msg = self.get(player_id).join_message
        if msg is None:
            msg = self.join_messages.get(player_id)
        if msg is None:
            return
        gmf(medium)(channel_id, msg.format(name=player_nick))

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
            self.get(id_).add_points_effect(self.effectbase.test_effect())

    def apply_effect(self, entity_id: str, effect_id: str, is_player_nick=False, is_effect_name=False) -> str:
        """ Applies an effect to a chatentity """
        with lock:
            effect = self.effectbase.get_effect(effect_id, is_name=is_effect_name)
            entity = self.get(entity_id, is_nick=is_player_nick)
            if effect is None:
                msg = 'Failed applying the effect to %s! It was probably not found...' % entity.nick
                logger.warn(msg)
                return msg
            entity.add_points_effect(effect)
            return '%s received effect: [%s]' % (entity.nick, effect.to_str())

    def use_item(self, item_id: str, user_id: str, target_id: str=None,
                 is_item_name=False, is_user_nick=False, is_target_nick=False) -> str:
        with lock:
            user = self.get(user_id, is_nick=is_user_nick)
            item = user.get_usable_item(item_id, is_name=is_item_name)
            if item is None:
                return '%s does not possess such an item!' % user.nick
            target = user
            if target_id is not None:
                target = self.get(target_id, is_nick=is_target_nick)
            return item.use(user, target)

    def add_item(self, player_id: str, item_id: str, is_player_nick=True, is_item_name=False) -> str:
        with lock:
            item = self.itembase.get_item(item_id, is_name=is_item_name)
            if item is None:
                return 'Failed creating item! Id does probably not exist...'
            self.get(player_id, is_nick=is_player_nick).add_usable_item(item)
            return 'Gave item %s to %s' % (item.item_id, player_id)
        pass

    def add_test_item(self, id_: str):
        with lock:
            item = self.itembase.test_item()
            logger.info(item.to_str())
            self.get(id_).add_usable_item(item)
        pass

    def add_to_ignore(self, id_: str, is_nick=False, duration=None) -> str:
        """ add a player to the ignore list """
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
        """ get players on the ignore list """
        with lock:
            items = []
            for id_, d in self.ignored_players.items():
                part, d = ('{n}', 0) if d is None else ('{n} ({d})', d)
                items.append(part.format(**{'n': self.get(id_).nick, 'd': time_to_str(d - time.time())}))
            return 'Ignored players: %s' % ', '.join(items)

    def remove_from_ignore(self, id_: str, is_nick=False) -> str:
        """ remove a player to the ignore list """
        with lock:
            id_ = id_ if not is_nick else self.nick_to_id.get(id_, id_)
            if id_ is None:
                return 'Failed removing %s from the ignore list! The player id was not found in the DB!' % id_
            if self.ignored_players.get(id_, False) is False:
                return '%s is not on the ignore list!' % id_
            self.ignored_players.pop(id_)
            self.save()
            return 'Removed %s from the ignore list!' % id_

    def __channels_by_type(self, type_: str) -> dict:
        return {
            'chat': self.chat_channels,
            'game': self.game_channels,
        }.get(type_)

    def __add_accepted(self, type_: str, callback_fun, id_: str, duration=None) -> str:
        channels = self.__channels_by_type(type_)
        with lock:
            if id_ in channels.keys():
                return '%s is already an accepted channel!' % id_
            channels[id_] = (duration + time.time()) if duration is not None else duration
            self.save()
            if duration is not None:
                self.queue.add(CallbackItem(duration, callback_fun, id_))
                return 'Added %s to the accepted channels list, will be removed in %s' % (id_, time_to_str(duration))
            return 'Added %s to the accepted channels list!' % id_

    def add_accepted_chat(self, id_: str, duration=None) -> str:
        """ add a channel to the list where one can get points for chatting """
        return self.__add_accepted('chat', self.remove_accepted_chat, id_, duration)

    def add_accepted_game(self, id_: str, duration=None) -> str:
        """ add a channel to the list where one can play chat games """
        return self.__add_accepted('game', self.remove_accepted_game, id_, duration)

    def __get_accepted(self, type_: str) -> str:
        channels = self.__channels_by_type(type_)
        with lock:
            items = []
            for id_, d in channels.items():
                part, d = ('{n}', 0) if d is None else ('{n} ({d})', d)
                items.append(part.format(**{'n': self.get(id_).id, 'd': time_to_str(d - time.time())}))
            return 'List of accepted channels: %s' % ', '.join(items)

    def get_accepted_chat(self) -> str:
        """ get list of channels where one can get points for chatting """
        return self.__get_accepted('chat')

    def get_accepted_game(self) -> str:
        """ get list of channels where one can play chat games """
        return self.__get_accepted('game')

    def is_accepted_for_games(self, channel_name: str):
        return channel_name in self.game_channels.keys()

    def __remove_accepted(self, type_: str, id_: str) -> str:
        channels = self.__channels_by_type(type_)
        with lock:
            if id_ is None:
                return 'Failed removing %s from the acepted channel list! The channel id was not found in the DB!' % id_
            if channels.get(id_, False) is False:
                return '%s is not an accepted channel!' % id_
            channels.pop(id_)
            self.save()
            return 'Removed %s from the accepted channels list!' % id_

    def remove_accepted_chat(self, id_: str) -> str:
        """ remove a channel from the list where one can get points for chatting """
        return self.__remove_accepted('chat', id_)

    def remove_accepted_game(self, id_: str) -> str:
        """ remove a channel from the list where one can play chat games"""
        return self.__remove_accepted('game', id_)
