import persistent.dict
import transaction
from modules.types import ChatType, GameType, PointType
from modules.utils import get_msg_fun as gmf
from modules.callbackqueue import CallbackQueue
from modules.chatbase import Chatbase
from modules.utils import get_logger

logger = get_logger('game')


class Game(persistent.Persistent):
    def __init__(self, chat_type: ChatType, channel: str, queue: CallbackQueue, on_end_callback,
                 game_type: GameType, point_type: PointType, chatbase: Chatbase):
        super(Game, self).__init__()
        self.players = persistent.dict.PersistentDict()  # name to points
        self.chat_type = chat_type
        self.channel = channel
        self.queue = queue
        self.chatbase = chatbase
        self.game_type = game_type
        self.point_type = point_type
        self.on_end_callback = on_end_callback
        self.is_running = True

    def print(self):
        raise NotImplementedError()

    def join(self, name: str, points: int):
        return self._reserve_points(name, points)

    def save(self):
        # should be locked by the child classes
        self._p_changed = True
        transaction.commit()

    def end(self):
        logger.debug('Game: end')
        self.is_running = False
        self.on_end_callback(self)

    def ended(self) -> bool:
        return not self.is_running

    def _reserve_points(self, name: str, amount: int, partial=False):
        """ reserves 'amount' point of its point_type """
        p, done = self.chatbase.get(name, is_nick=True).update_points(-amount, type_=self.point_type, partial=partial,
                                                                      mult_enabled=False)
        self.players[name] = self.players.get(name, 0) - p  # since we update with -amount
        self.save()
        logger.debug('Game: reserve %s, %s/%s, %s' % (name, amount, p, self.players))
        return done

    def _pay_winners(self, dct: dict, names: [str]):
        """ collects all points and distributes them to the winner(s) and informs them
            dct has {name, points} """
        logger.debug('Game: pay %s' % names)
        total = sum(list(dct.values()))
        points_per = total // len(names)
        for name in names:
            self.chatbase.get(name, is_nick=True).update_points(points_per, type_=self.point_type, mult_enabled=False)
            self._message(name, 'The game ended! You win %d points!' % points_per)
            logger.debug('Game: paying %s' % name)
        for name in dct.keys():
            if name in names:
                continue
            self._message(name, 'The game ended, someone else won!')
            self.save()

    def _message(self, name: str, msg: str):
        """ tries to message the player/channel in its chat_type """
        gmf(self.chat_type)(name, msg)

    def reset(self):
        """ return reserved points """
        for name, points in self.players:
            self.chatbase.get(name, is_nick=True).update_points(points, type_=self.point_type, mult_enabled=False)
