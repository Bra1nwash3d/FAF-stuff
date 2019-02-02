from modules.chatbase import Chatbase
import modules.eventbase as eventbase
import modules.timer as timer
import ZODB
import ZODB.FileStorage
import os


class X:
    def __init__(self):
        db_path = './data_chat/data_chat.fs'
        os.makedirs('/'.join([p for p in db_path.split('/')[:-1]]), exist_ok=True)
        storage = ZODB.FileStorage.FileStorage(db_path)
        self.db = ZODB.DB(storage)
        self.db_con = self.db.open()
        self.db_root = self.db_con.root
        try:
            self.db_root.chatbase.print()
        except:
            self.db_root.chatbase = Chatbase(eventbase.Eventbase(), timer.SpamProtect(['#aeolus']), None, None)
            self.db_root.chatbase.print()

        # self.db_root.chatbase.on_chat('this is a test', 'Washy', 'Washy', '#shadows')
        # self.db_root.chatbase.get('Washy').update_points('Washy', 1, type_=PointType.CHAT)
        # self.db_root.chatbase.get('859').update_points('Purpleheart', 1, type_=PointType.CHAT)

    def print_names(self):
        print(self.db_root.chatbase.get('Washy').get_point_message())
        print(self.db_root.chatbase.get('#aeolus').get_point_message())

    def print_all(self):
        print('\nAll entries in nick_to_id')
        for n, id_ in self.db_root.chatbase.nick_to_id.items():
            print(n, id_)

    def print_largest(self):
        print('\nAll entries in nick_to_id')
        print(self.db_root.chatbase.get_k_points_str())
        print(self.db_root.chatbase.get_k_points_str(largest=False))
        print(self.db_root.chatbase.get_k_points_str(incl_channels=False))
        print(self.db_root.chatbase.get_k_most_points_str(incl_channels=False))


x = X()
x.print_names()
x.print_all()
x.print_largest()
