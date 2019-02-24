import persistent
import persistent.dict
import persistent.list
import transaction
from modules.effectbase import EffectBase
from modules.utils import get_logger, points_to_level
from modules.utils import get_msg_fun as gmf
from modules.types import PointType, ChatType
from modules.effects import PointsEffect
from modules.items.item import UsableItem

logger = get_logger('chatentity')


class ChatEntity(persistent.Persistent):

    def __init__(self, id_):
        super(ChatEntity, self).__init__()
        self.id = id_
        self.nick = '_unknown_'
        self.points = persistent.dict.PersistentDict()
        self.point_sum = 0
        self.useable_items = persistent.dict.PersistentDict()
        self.points_mults = persistent.dict.PersistentDict()
        self.points_effects = persistent.list.PersistentList()
        self.join_message = None

    def migrate(self):
        """ to migrate the db when new class elements are added - call self.save() if you do """
        # self.x = self.__dict__.get('x', 'oh a new self.x!')
        # migrate existing effects
        for effect in self.points_effects:
            effect.migrate()

    def save(self):
        self._p_changed = True
        transaction.commit()

    def add_usable_item(self, item: UsableItem):
        item.merge(self.useable_items.pop(item.item_id) if item.item_id in self.useable_items else None)
        self.useable_items[item.item_id] = item
        logger.debug('added usable item to %s/%s, item: %s' % (self.id, self.nick, item.item_id))
        self.save()

    def get_usable_item(self, item_id: str, is_name=False):
        """ return the item of item_id """
        if not is_name:
            return self.useable_items.get(item_id)
        for item in self.useable_items.values():
            if item.has_id(item_id, is_name=is_name):
                return item
        return None

    def update_usable_items(self):
        remove_keys = []
        for k, item in self.useable_items.items():
            if item.uses <= 0:
                remove_keys.append(k)
        for k in remove_keys:
            self.useable_items.pop(k)
        self.save()

    def add_points_effect(self, effect: PointsEffect):
        if effect is None:
            logger.warn('Chatentity id:%s, nick:%s, tried applying None effect' % (self.id, self.nick))
            return
        self.points_effects.append(effect)
        effect.begin(self.update_points_effects, effect, begins=False)
        logger.debug('ChatEntity id:%s adding new effect, has %d' % (self.id, len(self.points_effects)))
        self.update_points_effects(effect, begins=True)

    def update_points_effects(self, effect: PointsEffect, begins=True):
        """ updates effects list and multipliers """
        self.points_mults.clear()
        self.points_effects, to_apply = EffectBase.get_updated_effects(self.points_effects)
        for e in to_apply:
            for k, v in e.get_adds().items():
                self.points_mults[k] = self.points_mults.get(k, 1) + v
        for e in to_apply:
            for k, v in e.get_mults().items():
                self.points_mults[k] = self.points_mults.get(k, 1) * v
        self.save()
        mults = self.__get_mults_strs()
        msg = 'A chat-effect {state}! [{effect}], changing your multipliers to {mults}!'.format(**{
            'state': 'begins' if begins else 'ended',
            'effect': effect.to_str(),
            'mults': '[%s]' % ', '.join(mults) if len(mults) > 0 else 'default',
        })
        gmf(ChatType.IRC)(self.nick, msg)
        logger.debug('ChatEntity id:%s updating effects: %s' % (self.id, [str(e) for e in self.points_effects]))
        logger.debug('ChatEntity id:%s has mults: %s' % (self.id, self.points_mults))

    def update_points(self, delta, nick=None, type_=PointType.CHAT, partial=False, mult_enabled=True) -> (int, bool):
        """
        Updating points and nick
        :returns points, bool whether successfully updated
        """
        self.nick = nick if nick is not None else self.nick
        points = int(delta) if not mult_enabled else int(delta*self.get_mult(type_=type_))
        if self.point_sum + points < 0:
            if partial:
                points = -self.point_sum
            else:
                return 0, False
        self.points[type_] = self.points.get(type_, 0) + points
        self.point_sum += points
        self.save()
        logger.debug('updated {id}:{nick} by d:{delta}/p:{points} points of type "{type}", total is {p}'.format(**{
            'id': self.id,
            'nick': nick,
            'p': self.points[type_],
            'type': type_,
            'delta': delta,
            'points': points,
        }))
        return points, True

    def get_level(self):
        level, _ = points_to_level(self.point_sum)
        return level

    def get_points(self, type_=None) -> int:
        if type_ is None:
            return self.point_sum
        return self.points.get(type_, 0)

    def get_point_message(self) -> str:
        msg_parts, sum_ = [], 0
        for type_ in PointType:
            p = self.get_points(type_)
            if p != 0:
                msg_parts.append('%i from %s' % (p, PointType.as_str(type_)))
        level, rem_points = points_to_level(self.point_sum)
        return "{nick} is level {lvl} with {p} points ({rp} to next level, {parts})".format(**{
            'nick': self.nick,
            'lvl': level,
            'p': self.point_sum,
            'rp': rem_points,
            'parts': ", ".join(msg_parts)
        })

    def __get_mults_strs(self) -> list:
        msg_parts = []
        for k, v in self.points_mults.items():
            if v != 1:
                msg_parts.append('%s by x%.2f' % (PointType.as_str(k), v))
        return msg_parts

    def get_mult_message(self) -> str:
        msg_parts, msg = self.__get_mults_strs(), ''
        if len(msg_parts) > 0:
            msg = ', changing point multipliers to: [%s]' % ', '.join(msg_parts)
        return "{nick} has {n} effects running{mults}".format(**{
            'nick': self.nick,
            'n': len(self.points_effects),
            'mults': msg,
        })

    def get_effects_message(self) -> str:
        mults_msg_parts, mults_msg = self.__get_mults_strs(), ''
        if len(mults_msg_parts) > 0:
            mults_msg = ', changing point multipliers to: [%s]' % ', '.join(mults_msg_parts)
        msg = ["%s has %i effects running (not all may stack)%s" % (self.nick, len(self.points_effects), mults_msg)]
        for e in self.points_effects:
            msg.append(' - %s' % e.to_str())
        return '\n'.join(msg)

    def get_usable_items_message(self, show_hidden=False) -> str:
        items, hidden_items = self.useable_items, self.useable_items
        if not show_hidden:
            items, hidden_items = UsableItem.split_visible_hidden(list(self.useable_items.values()))
        num, numh = len(items), len(hidden_items)
        if num == 0:
            return '%s has no items!' % self.nick
        msg = ['%s has %d items:' % (self.nick, num)]
        for item in items:
            msg.append(' - %s' % item.to_str())
        return '\n'.join(msg)

    def get_mult(self, type_=PointType.CHAT) -> int:
        return self.points_mults.get(type_, 1)

    @property
    def is_channel(self) -> bool:
        return self.id.startswith('#')

    @property
    def is_player(self) -> bool:
        return not self.is_channel
