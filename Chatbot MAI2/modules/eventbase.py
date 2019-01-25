import persistent.list
import transaction
from modules.event import *
from modules.types import CommandType, EventType
from modules.get_logger import get_logger

logger = get_logger('eventbase')


class Eventbase(persistent.Persistent):
    def __init__(self, ):
        super(Eventbase, self).__init__()
        self.events = persistent.list.PersistentList()
        self.next_id = 0
        logger.info('Created new Eventbase')

    def save(self):
        self._p_changed = True
        transaction.commit()

    def add_event(self, e):
        e.id = self.next_id
        self.events.append(e)
        self.next_id += 1
        self.save()
        logger.debug('added new event: %s' % e)

    def add_command_event(self, type_: CommandType, by_, target=None, args=None, spam_protect_time=None):
        event = CommandEvent(type_, by_, target, args, spam_protect_time)
        self.add_event(event)

    def add_chat_tip_event(self, by, target, points_desired, points_tipped):
        event = ChatTipEvent(by, target, points_desired, points_tipped)
        self.add_event(event)

    def print(self):
        logger.info('Eventbase has {n} entities'.format(**{
            'n': len(self.events),
        }))

    @staticmethod
    def filter_events(events, filter_fun):
        filtered = []
        for e in events:
            if filter_fun(e):
                filtered.append(e)
        return filtered

    def filter_type(self, types, events=None):
        """ types is a list, can be [None] to include all """
        events = events if events is not None else self.events
        if types.count(None) == len(types):
            return events

        def has_type(e):
            return e.type in types

        return Eventbase.filter_events(events, has_type)

    def filter_time(self, t0d=None, t1d=0, events=None):
        """ events happening between t0d and t1d, relative to current time
            e.g. t0d=60, t1d=30, are the events in the past minute - those in the past 30 seconds """
        events = events if events is not None else self.events
        t0d = t0d if t0d is not None else time.time()
        t1d = t1d if t1d is not None else 0
        t0, t1 = time.time()-t0d, time.time()-t1d

        def in_time(e):
            return t0 <= e.time <= t1

        return Eventbase.filter_events(events, in_time)

    def filter_by(self, by, events=None):
        """ events happening between t0d and t1d, relative to current time
            e.g. t0d=60, t1d=30, are the events in the past minute - those in the past 30 seconds """
        events = events if events is not None else self.events
        if by is None:
            return events

        def is_by(e):
            return e.is_by(by)

        return Eventbase.filter_events(events, is_by)

    def get_command_events(self, types):
        """ types is a list, can be [None] to include all """

    def print_events(self, events=None):
        events = events if events is not None else self.events
        for e in events:
            logger.info(e)
