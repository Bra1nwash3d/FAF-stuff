import time
import persistent.dict
import transaction
from modules.get_logger import get_logger

logger = get_logger('spam_protect')


class SpamProtect:
    def __init__(self, protected_channels):
        """ prefer stored protected_channels and new timer/default_cd """
        self.channels = persistent.dict.PersistentDict()  # store of when commands were used last
        self.timer = persistent.dict.PersistentDict()  # store of command dependent cooldowns
        self.protected_channels = protected_channels if protected_channels is not None else []

        # vars
        self.default_cd = 0

        logger.info('Created new SpamProtect, watches over: %s' % str(self.protected_channels))

    def update_vars(self, default_cd=None, **_):
        # function to set misc vars
        self.default_cd = default_cd if default_cd is not None else self.default_cd
        self.save()

    def update_timer(self, timer=None):
        self.timer = timer if timer is not None else self.timer
        logger.info('Updated SpamProtect timer %s' % str(self.timer))
        self.save()

    def save(self):
        self._p_changed = True
        transaction.commit()

    def print(self):
        logger.info('Loaded SpamProtect, watches over: %s' % str(self.protected_channels))

    def is_in_protected_channels(self, channel):
        return channel in self.channels

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

