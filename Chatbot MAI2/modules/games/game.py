import persistent.dict
import transaction
from modules.types import ChatType, GameType, PointType
from modules.utils import get_msg_fun as gmf
from modules.callbackqueue import CallbackQueue
from modules.chatbase import Chatbase
from modules.eventbase import Eventbase
from modules.utils import get_logger

logger = get_logger('game')


class Game(persistent.Persistent):
    def __init__(self, chat_type: ChatType, channel: str, requested_by: str, queue: CallbackQueue, on_end_callback,
                 game_type: GameType, point_type: PointType, chatbase: Chatbase, eventbase: Eventbase):
        super(Game, self).__init__()
        self.players = persistent.dict.PersistentDict()  # id_ to points
        self.id_to_name = {}
        self.chat_type = chat_type
        self.channel = channel
        self.requested_by = requested_by
        self.queue = queue
        self.chatbase = chatbase
        self.eventbase = eventbase
        self.game_type = game_type
        self.point_type = point_type
        self.on_end_callback = on_end_callback
        self.is_running = True

    def migrate(self):
        """ to migrate the db when new class elements are added - call self.save() if you do """
        raise NotImplementedError()

    def join(self, id_: str, name: str, points: int):
        self.id_to_name[id_] = name
        return self._reserve_points(id_, name, points)

    def save(self):
        # should be locked by the child classes
        self._p_changed = True
        transaction.commit()

    def end(self):
        logger.debug('Game: end')
        self.players.clear()  # remove reserved points, they should be paid by now
        self.is_running = False
        self.on_end_callback(self)

    def ended(self) -> bool:
        return not self.is_running

    def _reserve_points(self, id_: str, name: str, amount: int, partial=False):
        """ reserves 'amount' point of its point_type """
        p, done = self.chatbase.get(id_).update_points(-amount, type_=self.point_type, partial=partial,
                                                       mult_enabled=False)
        self.players[id_] = self.players.get(id_, 0) - p  # since we update with -amount
        self.save()
        logger.debug('Game: reserve %s/%s, %s/%s, %s' % (id_, name, amount, p, self.players))
        return done

    def _pay_winners(self, dct: dict, winner_ids: [str]):
        """ collects all points and distributes them to the winner(s) and informs them
            dct has {name, points} """
        logger.debug('Game: pay %s' % winner_ids)
        total = sum(list(dct.values()))
        points_per = total // len(winner_ids)
        for id_ in self.players.keys():
            if id_ in winner_ids:
                self.chatbase.get(id_).update_points(points_per, type_=self.point_type, mult_enabled=False)
                self._message(id_, 'The game ended! You win %d points!' % points_per)
                logger.debug('Game: paying %s' % id_)
            else:
                self._message(id_, 'The game ended, someone else won!')
        self.save()

    def _message(self, id_: str, msg: str):
        """ tries to message the player/channel in its chat_type """
        name = self.id_to_name.get(id_, id_)  # may message the channel
        gmf(self.chat_type)(name, msg)

    def reset(self):
        """ return reserved points """
        for name, points in self.players.items():
            self.chatbase.get(name, is_nick=True).update_points(points, type_=self.point_type, mult_enabled=False)
