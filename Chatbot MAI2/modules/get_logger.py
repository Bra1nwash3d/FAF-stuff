import logging

loggers = {}


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
