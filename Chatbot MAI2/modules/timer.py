import time
import persistent.dict
import transaction
from modules.get_logger import get_logger

logger = get_logger('spam_protect')


class SpamProtect:
    def __init__(self, protected_channels):
        """ prefer stored protected_channels and new timer/default_cd """
        self.default_cd = 0
        self.channels = persistent.dict.PersistentDict()  # store of when commands were used last
        self.timer = persistent.dict.PersistentDict()  # store of command dependent cooldowns
        self.protected_channels = protected_channels if protected_channels is not None else []
        logger.info('Created new SpamProtect, watches over: %s' % str(self.protected_channels))

    def print(self):
        logger.info('Loaded SpamProtect, watches over: %s' % str(self.protected_channels))

    def update_timer(self, timer=None, default_cd=None):
        self.timer = timer if timer is not None else self.timer
        self.default_cd = default_cd if default_cd is not None else 0
        logger.info('Updated timer/defaultcd %s, %s' % (str(self.timer), str(default_cd)))
        # logger.info('SpamProtect watches over: %s' % str(self.protected_channels))

    def get_remaining(self, channel, cmd, include_unprotected=False):
        if channel not in self.channels.keys():
            self.channels[channel] = persistent.dict.PersistentDict()
        if channel in self.protected_channels or include_unprotected:
            return (self.channels[channel].get(cmd, 0) + self.timer.get(cmd, self.default_cd)) - time.time()
        return 0

    def set_now(self, channel, cmd):
        if channel not in self.channels.keys():
            self.channels[channel] = persistent.dict.PersistentDict()
        self.channels[channel][cmd] = time.time()
        logger.debug('Spamprotect: set to now: %s, %s' % (channel, cmd))
        transaction.commit()

    def is_spam(self, channel, cmd, update=True, include_unprotected=False):
        rem_time = self.get_remaining(channel, cmd, include_unprotected)
        logger.debug('Spamprotect: time left: %s, %s, %s' % (channel, cmd, rem_time))
        if update and rem_time <= 0:
            self.set_now(channel, cmd)
        return rem_time > 0, rem_time

