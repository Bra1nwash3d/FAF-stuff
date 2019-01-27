import persistent
import time
from modules.get_logger import get_logger
from modules.types import EventType, CommandType

logger = get_logger('event')


class Event(persistent.Persistent):
    """ don't make events of this class, use the subclasses """

    def __init__(self, type_, by):
        super(Event, self).__init__()
        self.id = None  # set a bit later
        self.type = type_
        self.time = time.time()
        self.by = by

    def is_type(self, type_: EventType):
        return type_ in [self.type, EventType.ANY, None]

    def is_by(self, by):
        return self.by == by

    def __str__(self):
        return 'Event id:{id}, type:{type}'.format(**{
            'id': self.id,
            'type': self.type,
        })


class CommandEvent(Event):
    def __init__(self, command_type: CommandType, by, target, args, spam_protect_time=None):
        super(CommandEvent, self).__init__(EventType.COMMAND, by)
        self.command_type = command_type
        self.target = target
        self.args = args
        self.spam_protect_time = spam_protect_time

    def get_spam_protect_time(self):
        return self.spam_protect_time if self.spam_protect_time is not None else 0

    def __str__(self):
        return 'Event id:{id}, type:{type}, c_type:{ct}, by:{by}, target:{target}, spam:{s}, args:{args}'.format(**{
            'id': self.id,
            'type': self.type,
            'ct': self.command_type,
            'by': self.by,
            'target': self.target,
            'args': str(self.args),
            's': self.spam_protect_time,
        })


class ChatTipEvent(Event):
    def __init__(self, by, target, p_desired, p_tipped):
        super(ChatTipEvent, self).__init__(EventType.CHATTIP, by)
        self.target = target
        self.p_desired = p_desired
        self.p_tipped = p_tipped

    def __str__(self):
        return 'Event id:{id}, type:{type}, by:{by}, target:{target}, desired:{p0}, points:{p1}'.format(**{
            'id': self.id,
            'type': self.type,
            'by': self.by,
            'target': self.target,
            'p0': self.p_desired,
            'p1': self.p_tipped,
        })


class OnKickEvent(Event):
    def __init__(self, by, target, channel, msg: str, points: int):
        super(OnKickEvent, self).__init__(EventType.KICK, by)
        self.target = target
        self.channel = channel
        self.msg = msg
        self.points = points

    def __str__(self):
        return 'Event id:{id}, type:{type}, by:{by}, target:{target}, channel:{c}, msg:{msg}, points: {p}'.format(**{
            'id': self.id,
            'type': self.type,
            'by': self.by,
            'target': self.target,
            'c': self.channel,
            'msg': self.msg,
            'p': self.points
        })
