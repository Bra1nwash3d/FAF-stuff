import random
from modules.utils import time_to_str
from modules.games.game import Game
from modules.types import ChatType, GameType, PointType
from modules.callbackqueue import CallbackQueue
from modules.callbackitem import CallbackItem
from modules.chatbase import Chatbase
from modules.utils import get_logger, get_lock

logger = get_logger('roulette_game')
lock = get_lock('roulette_game')


class RouletteGame(Game):
    def __init__(self, chat_type: ChatType, channel: str, queue: CallbackQueue, on_end_callback, chatbase: Chatbase,
                 duration: int):
        super(RouletteGame, self).__init__(chat_type, channel, queue, on_end_callback,
                                           GameType.ROULETTE, PointType.ROULETTE, chatbase)
        self.queue.add(CallbackItem(duration, self.select_winner))
        self.total_points = 0
        self.save()
        self._message(self.channel, "A new roulette game was started! You have %s to bet your points!"
                      % time_to_str(duration))
        logger.debug('Created new RouletteGame')

    def join(self, name: str, points: int):
        with lock:
            logger.debug('RouletteGame join: %s, %s, %s' % (self.channel, name, points))
            if super().join(name, points):
                self.total_points += points
                msg = 'You added {p} points to the roulette game in {c}, your win chance is {e}%!'
                self._message(name, msg.format(**{
                    'p': points,
                    'c': self.channel,
                    'e': int(self.players.get(name, 0)*1000/self.total_points)/10,
                }))
                return
            self._message(self.channel, 'Failed adding points for %s :(' % name)

    def print(self):
        with lock:
            logger.debug('Loaded RouletteGame, TODO')

    def select_winner(self):
        with lock:
            winners = random.choices(list(self.players.keys()), list(self.players.values()))
            logger.debug('RouletteGame select winner %s' % winners)
            self._pay_winners(self.players, winners)
            self._message(self.channel, 'The roulette game ended! Winner: %s' % ', '.join(winners))
            self.end()
