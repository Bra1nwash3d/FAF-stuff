import persistent
import persistent.dict
import transaction
from modules.get_logger import get_logger
from modules.types import PointType

logger = get_logger('chatentity')


class ChatEntity(persistent.Persistent):

    def __init__(self, id_):
        super(ChatEntity, self).__init__()
        self.id = id_
        self.nick = '_unknown_'
        self.points = persistent.dict.PersistentDict()
        self.point_sum = 0
        self.mults = persistent.dict.PersistentDict()
        self.effects = persistent.dict.PersistentDict()
        # TODO effects, add, on_change, queue, ...

    def save(self):
        self._p_changed = True
        transaction.commit()

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

    def get_mult(self, type_=PointType.CHAT) -> int:
        return self.mults.get(type_, 1)

    @property
    def is_channel(self) -> bool:
        return self.id.startswith('#')

    @property
    def is_player(self) -> bool:
        return not self.is_channel
