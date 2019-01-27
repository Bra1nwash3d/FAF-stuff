import persistent
import persistent.dict
import persistent.list
import transaction
from modules.utils import get_logger
from modules.types import PointType
from modules.effects import PointsEffect

logger = get_logger('chatentity')


class ChatEntity(persistent.Persistent):

    def __init__(self, id_):
        super(ChatEntity, self).__init__()
        self.id = id_
        self.nick = '_unknown_'
        self.points = persistent.dict.PersistentDict()
        self.point_sum = 0
        self.mults = persistent.dict.PersistentDict()
        self.effects = persistent.list.PersistentList()
        # TODO effects, add, on_change, queue, ...

    def save(self):
        self._p_changed = True
        transaction.commit()

    def add_effect(self, effect: PointsEffect):
        self.effects.append(effect)
        effect.begin(self)
        logger.debug('ChatEntity id:%s adding new effect, has %d' % (self.id, len(self.effects)))
        self.update_effects()

    def update_effects(self):
        # reset multipliers
        self.mults.clear()
        # clear effects that have run out
        j = 0
        while j < len(self.effects):
            e = self.effects[j]
            if e.is_expired():
                self.effects.pop(j)
            else:
                j += 1
        # group remaining effects into groups, effects within groups can not stack TODO
        # select strongest effect of each group and modify mults, using all right now TODO
        for e in self.effects:
            for k, v in e.get_mults().items():
                self.mults[k] = self.mults.get(k, 1) * v
        self.save()
        logger.debug('ChatEntity id:%s updating effects: %s' % (self.id, [str(e) for e in self.effects]))
        logger.debug('ChatEntity id:%s has mults: %s' % (self.id, self.mults))

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
        logger.debug('udpated {id}:{nick} by d:{delta}/p:{points} points of type "{type}", total is {p}'.format(**{
            'id': self.id,
            'nick': nick,
            'p': self.points[type_],
            'type': type_,
            'delta': delta,
            'points': points,
        }))
        return points, True

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
        return "%s has %i points (%s)" % (self.nick, self.point_sum, ", ".join(msg_parts))

    def get_mult_message(self) -> str:
        msg_parts, sum_ = [], 0
        for k, v in self.mults.items():
            if v != 1:
                msg_parts.append('%s: %.2f' % (PointType.as_str(k), v))
        return "%s has %i effects running, changing point multipliers to: [%s]"\
               % (self.nick, len(self.effects), ", ".join(msg_parts))

    def get_effects_message(self) -> str:
        msg = ["%s has %i effects running (not all may stack)" % (self.nick, len(self.effects))]
        for e in self.effects:
            msg.append(' - %s' % e.to_str())
        return '\n'.join(msg)

    def get_mult(self, type_=PointType.CHAT) -> int:
        return self.mults.get(type_, 1)

    @property
    def is_channel(self) -> bool:
        return self.id.startswith('#')

    @property
    def is_player(self) -> bool:
        return not self.is_channel
