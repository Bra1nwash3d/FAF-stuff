import logging
import threading
from modules.types import ChatType


LEVEL_TO_POINTS = [0, 50]  # to be filled
loggers = {}
locks = {}
message_funs = {}


def get_logger(name='bot', level='info'):
    if name in loggers:
        return loggers.get(name)
    level = {
        'info': logging.INFO,
        'debug': logging.DEBUG,
    }.get(level.lower())
    logger = logging.getLogger(name)
    logger.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    logger.addHandler(ch)
    return logger


def get_lock(name='lock'):
    if name in locks:
        return locks.get(name)
    locks[name] = threading.RLock()
    return locks.get(name)


def level_to_points(level: int) -> int:
    global LEVEL_TO_POINTS
    if level < len(LEVEL_TO_POINTS):
        return LEVEL_TO_POINTS[level]
    # the magical formula!
    LEVEL_TO_POINTS.append(LEVEL_TO_POINTS[-1] + 50*len(LEVEL_TO_POINTS))
    return level_to_points(level)


def points_to_level(points: int) -> int:
    """ may return a too small level if it's not cached """
    for i, p in enumerate(LEVEL_TO_POINTS):
        if points < p:
            return i
    return len(LEVEL_TO_POINTS)


def try_fun(fun, default, *args, **kwargs):
    try:
        return fun(*args, **kwargs)
    except:
        return default


def time_to_str(seconds: int) -> str:
    # i know datetime exists, but it does not have access to hours/minutes
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return "%dh:%02dm:%02ds" % (h, m, s)
    if m > 0:
        return "%02dm:%02ds" % (m, s)
    return "%02ds" % s


def not_pinging_name(name):
    return '%s%s%s' % (name[0:len(name)-1], '.', name[len(name)-1])


failure_logger = get_logger('utils')


def __log_msg_fun(type_: ChatType):
    def wrapped(target, msg):
        failure_logger.warning('[missing logger for %s] %s: %s' % (type_.value, target, msg))

    return wrapped


def set_msg_fun(type_: ChatType, fun):
    message_funs[type_] = fun


def get_msg_fun(type_: ChatType):
    fun = message_funs.get(type_, None)
    if fun is None:
        return __log_msg_fun(type_)
    return fun
