import enum


class PointType(enum.Enum):
    CHAT = 'chat'
    KICK = 'kick'
    CHATTIP = 'chattip'
    ROULETTE = 'roulette'

    @staticmethod
    def as_str(type_):
        """ used to assemble 'x points by doing y' messages """
        return {
            PointType.CHATTIP: 'tips',
        }.get(type_, type_.value)

    @staticmethod
    def from_str(str_):
        if str_ is None:
            return None
        for e in PointType:
            if e.value == str_:
                return e
        return {
            'sum': None,
            'tip': PointType.CHATTIP,
            'tips': PointType.CHATTIP,
        }.get(str_.lower(), None)


class CommandType(enum.Enum):
    JOIN = 'join'
    LEAVE = 'leave'
    HIDDEN = 'hidden'
    RELOAD = 'reload'
    CD = 'cd'
    CHAIN = 'chain'
    CHAINPROB = 'chainprob'
    CHATLVL = 'chatlvl'
    CHATEFFECTS = 'chateffects'
    CHATLADDER = 'chatladder'
    CHATEVENTS = 'chatevents'
    CHATTIP = 'chattip'
    CHATROULETTE = 'chatroulette'
    ADMINBACKUP = 'adminbackup'
    ADMINEFFECTS = 'admineffects'
    ADMINIGNORE = 'adminignore'
    ADMINCHANNELS = 'adminchannels'
    ADMINRESET = 'adminreset'

    @staticmethod
    def from_str(str_):
        if str_ is None:
            return None
        for e in CommandType:
            if e.value == str_:
                return e
        return {
            'tip': CommandType.CHATTIP,
        }.get(str_.lower(), None)


class EventType(enum.Enum):
    ANY = 'any'
    KICK = 'kick'
    BAN = 'ban'
    MODE = 'mode'
    COMMAND = 'command'
    CHATTIP = 'chattip'
    ROULETTEGAME = 'roulette'

    @staticmethod
    def from_str(str_):
        if str_ is None:
            return None
        for e in EventType:
            if e.value == str_:
                return e
        return {
            'tip': EventType.CHATTIP,
            'chatroulette': EventType.ROULETTEGAME,
        }.get(str_.lower(), None)


class GameType(enum.Enum):
    ROULETTE = 'roulette'

    @staticmethod
    def from_str(str_):
        if str_ is None:
            return None
        for e in GameType:
            if e.value == str_:
                return e
        return {
        }.get(str_.lower(), None)


class ChatType(enum.Enum):
    IRC = 'irc'
    IDK = 'idk'
