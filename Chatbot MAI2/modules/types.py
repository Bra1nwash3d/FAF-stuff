import enum


class PointType(enum.Enum):
    CHAT = 0
    TIP = 1

    @staticmethod
    def as_str(type_):
        """ used to assemble 'x points by doing y' messages """
        return {
            PointType.CHAT: 'chat',
            PointType.TIP: 'tips',
        }.get(type_, 'unknown')

    @staticmethod
    def from_str(str_):
        return {
            'sum': None,
            'chat': PointType.CHAT,
            'tip': PointType.TIP,
            'chattip': PointType.TIP,
        }.get(str_.lower(), None)


class CommandType(enum.Enum):
    JOIN = 0
    LEAVE = 1
    HIDDEN = 2
    CD = 3
    CHATLVL = 100
    CHATLADDER = 101
    CHATEVENTS = 102
    CHATTIP = 103

    @staticmethod
    def from_str(str_):
        return {
            'join': CommandType.JOIN,
            'leave': CommandType.LEAVE,
            'hidden': CommandType.HIDDEN,
            'cd': CommandType.CD,
            'chatlvl': CommandType.CHATLVL,
            'chatladder': CommandType.CHATLADDER,
            'chatevents': CommandType.CHATEVENTS,
            'chattip': CommandType.CHATTIP,
        }.get(str_.lower(), None)


class EventType(enum.Enum):
    ANY = 0
    COMMAND = 1
    KICK = 2
    BAN = 3
    MODE = 4
    CHATTIP = 103

    @staticmethod
    def from_str(str_):
        return {
            'any': EventType.ANY,
            'command': EventType.COMMAND,
            'kick': EventType.KICK,
            'ban': EventType.BAN,
            'mode': EventType.MODE,
            'chattip': EventType.CHATTIP,
        }.get(str_.lower(), None)
