import modules.eventbase as eventbase
from modules.types import PointType, EventType, CommandType
import ZODB
import ZODB.FileStorage
import os


class X:
    def __init__(self):
        db_path = './data/data.fs'
        os.makedirs('/'.join([p for p in db_path.split('/')[:-1]]), exist_ok=True)
        storage = ZODB.FileStorage.FileStorage(db_path)
        self.db = ZODB.DB(storage)
        self.db_con = self.db.open()
        self.db_root = self.db_con.root
        try:
            self.db_root.eventbase.print()
        except:
            self.db_root.eventbase = eventbase.Eventbase()
            self.db_root.eventbase.print()

    def print_commands(self):
        events = self.db_root.eventbase.filter_type([EventType.COMMAND])
        self.db_root.eventbase.print_events(events)

    def print_in_past_time(self, t=4750):
        events = self.db_root.eventbase.filter_time(t0d=t)
        self.db_root.eventbase.print_events(events)

    def print_all(self):
        self.db_root.eventbase.print_events()


x = X()
# x.print_commands()
x.print_in_past_time()
# x.print_all()
