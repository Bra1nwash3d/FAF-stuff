import random
from modules.utils import time_to_str
from modules.games.game import Game
from modules.types import ChatType, GameType, PointType
from modules.callbackqueue import CallbackQueue
from modules.callbackitem import CallbackItem
from modules.chatbase import Chatbase
from modules.eventbase import Eventbase
from modules.utils import get_logger, get_lock

logger = get_logger('roulette_game')
lock = get_lock('roulette_game')


class RouletteGame(Game):
    def __init__(self, chat_type: ChatType, channel: str, requested_by: str, queue: CallbackQueue, on_end_callback,
                 chatbase: Chatbase, eventbase: Eventbase, duration: int):
        super(RouletteGame, self).__init__(chat_type, channel, requested_by, queue, on_end_callback,
                                           GameType.ROULETTE, PointType.ROULETTE, chatbase, eventbase)
        self.queue.add(CallbackItem(duration, self.select_winner))
        self.total_points = 0
        self.save()
        self._message(self.channel, "A new roulette game was started! You have %s to bet your points!"
                      % time_to_str(duration))
        logger.debug('Created new RouletteGame')

    def migrate(self):
        """ to migrate the db when new class elements are added - call self.save() if you do """
        with lock:
            # self.x = self.__dict__.get('x', 'oh a new self.x!')
            pass

    def join(self, id_: str, name: str, points: int):
        with lock:
            logger.debug('RouletteGame join: %s, %s/%s, %s' % (self.channel, id_, name, points))
            if super().join(id_, name, points):
                self.total_points += points
                msg = 'You added {p} points to the roulette game in {c}, your win chance is {e}%!'
                self._message(id_, msg.format(**{
                    'p': points,
                    'c': self.channel,
                    'e': int(self.players.get(id_, 0)*1000/self.total_points)/10,
                }))
                return
            self._message(self.channel, 'Failed adding points for %s :(' % name)

    def select_winner(self):
        with lock:
            winners = random.choices(list(self.players.keys()), list(self.players.values()))  # winner ids
            logger.debug('RouletteGame select winner ids %s' % winners)
            self._pay_winners(self.players, winners)
            self.eventbase.add_game_roulette_event(self.requested_by, self.channel, self.players, winners)
            winners_str = [self.id_to_name.get(w, w) for w in winners]
            self._message(self.channel, 'The roulette game ended! Winner: %s' % ', '.join(winners_str))
            self.end()
