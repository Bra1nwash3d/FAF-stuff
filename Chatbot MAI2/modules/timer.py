import time
import persistent.dict
import transaction
from modules.utils import get_logger, get_lock

logger = get_logger('spam_protect')
lock = get_lock('spam_protect')


class SpamProtect:
    def __init__(self, protected_channels):
        """ prefer stored protected_channels and new timer/default_cd """
        self.channels = persistent.dict.PersistentDict()  # store of when commands were used last
        self.timer = persistent.dict.PersistentDict()  # store of command dependent cooldowns
        self.protected_channels = protected_channels if protected_channels is not None else []

        # vars
        self.default_cd = 60

        logger.info('Created new SpamProtect, watches over: %s' % str(self.protected_channels))

    def reset(self):
        with lock:
            self.channels.clear()
            self.timer.clear()
            # self.protected_channels.clear()
            self.save()
            logger.info('Reset SpamProtect')

    def migrate(self):
        """ to migrate the db when new class elements are added - call self.save() if you do """
        with lock:
            # self.x = self.__dict__.get('x', 'oh a new self.x!')
            pass

    def update_vars(self, default_cd=None, protected_channels=None, **_):
        # function to set misc vars
        with lock:
            self.default_cd = default_cd if default_cd is not None else self.default_cd
            self.protected_channels = protected_channels if protected_channels is not None else self.protected_channels
            self.save()
            logger.info('SpamProtect, updating defaults %s / %s' % (default_cd, protected_channels))

    def update_timer(self, timer=None):
        with lock:
            self.timer = timer if timer is not None else self.timer
            logger.info('SpamProtect, updating timer: %s' % str(self.timer))
            self.save()

    def save(self):
        with lock:
            self._p_changed = True
            transaction.commit()

    def print(self):
        with lock:
            logger.info('Loaded SpamProtect, watches over: %s' % str(self.protected_channels))

    def is_in_protected_channels(self, channel: str):
        with lock:
            return channel in self.channels

    def get_remaining(self, channel: str, cmd: str, include_unprotected=False) -> float:
        with lock:
            logger.debug('Spamprotect: get remaining: %s, %s, %s' % (channel, cmd, include_unprotected))
            if channel not in self.channels.keys():
                self.channels[channel] = persistent.dict.PersistentDict()
            if channel in self.protected_channels or include_unprotected:
                logger.debug('Spamprotect: xxxxx %s' % self.timer.get(cmd, self.default_cd))
                logger.debug('Spamprotect: xxxxx %s' % self.timer)
                logger.debug('Spamprotect: xxxxx %s' % self.default_cd)
                return (self.channels[channel].get(cmd, 0) + self.timer.get(cmd, self.default_cd)) - time.time()
            return 0.0

    def set_now(self, channel: str, cmd: str):
        with lock:
            if channel not in self.channels.keys():
                self.channels[channel] = persistent.dict.PersistentDict()
            self.channels[channel][cmd] = time.time()
            logger.debug('Spamprotect: set to now: %s, %s' % (channel, cmd))
            transaction.commit()

    def is_spam(self, channel: str, cmd: str, update=True, include_unprotected=False) -> (bool, float):
        with lock:
            rem_time = self.get_remaining(channel, cmd, include_unprotected)
            logger.debug('Spamprotect: time left: %s, %s, %s' % (channel, cmd, rem_time))
            if update and rem_time <= 0:
                self.set_now(channel, cmd)
            return rem_time > 0, rem_time
