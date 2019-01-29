import persistent.dict
import transaction
from modules.utils import get_logger, get_lock
from modules.callbackqueue import CallbackQueue
from modules.eventbase import Eventbase
from modules.types import *
from modules.effectbase import EffectBase
from modules.chatbase import Chatbase
from modules.timer import SpamProtect
from modules.games.game import Game
from modules.games.roulette import RouletteGame

logger = get_logger('gamebase')
lock = get_lock('gamebase')


class Gamebase(persistent.Persistent):
    def __init__(self, eventbase: Eventbase, queue: CallbackQueue, chatbase: Chatbase, effectbase: EffectBase,
                 spam_protect: SpamProtect):
        super(Gamebase, self).__init__()
        self.games = persistent.dict.PersistentDict()       # current games
        self.prev_games = persistent.dict.PersistentDict()  # previous games, e.g. to reveal cards after the game
        self.eventbase = eventbase
        self.effectbase = effectbase
        self.chatbase = chatbase
        self.spam_protect = spam_protect
        self.queue = queue
        self.game_cooldowns = {}
        self.default_game_cooldown = 30
        self.save()
        logger.info('Created new Gamebase')

    def update_vars(self, game_cooldowns=None, default_game_cooldown=None, **_):
        with lock:
            # function to set misc vars
            self.default_game_cooldown = \
                default_game_cooldown if default_game_cooldown is not None else self.default_game_cooldown
            if game_cooldowns is not None:
                self.game_cooldowns.update(game_cooldowns)
            self.save()
            logger.info('Gamebase, updating default_cd:%s, cds:%s' % (default_game_cooldown, game_cooldowns))

    def print(self):
        with lock:
            logger.info('Loaded Gamebase, TODO')

    def save(self):
        with lock:
            self._p_changed = True
            transaction.commit()

    def reset(self):
        with lock:
            # TODO go through games and .reset them
            self.games.clear()
            self.save()
            logger.info('Reset Gamebase')

    def __get_game(self, channel: str, game_type: GameType, prev=False) -> Game:
        with lock:
            games = self.games if not prev else self.prev_games
            if not self.chatbase.is_accepted_for_games(channel):
                raise ValueError('Games are not enabled in channel %s!' % channel)
            if channel not in games.keys():
                games[channel] = persistent.dict.PersistentDict()
            return games[channel].get(game_type, None)

    def get_roulette_game(self, chat_type: ChatType, channel: str) -> RouletteGame:
        # TODO check with spamprotect
        # TODO make roulette game duration settable
        with lock:
            game = self.__get_game(channel, GameType.ROULETTE)
            if game is None:
                game = RouletteGame(chat_type, channel, self.queue, self.remove_game, self.chatbase, 30)  # TODO
                self.games[channel][GameType.ROULETTE] = game
            return game

    def remove_game(self, game: Game):
        # callback for games that ended
        # TODO update spamprotect
        logger.info('remove game: %s' % game.game_type)
        with lock:
            if game is None:
                return
            try:
                self.__get_game(game.channel, game.game_type, prev=False)  # just to make sure the dict stuff exists
                self.__get_game(game.channel, game.game_type, prev=True)   # just to make sure the dict stuff exists
                game = self.games[game.channel].pop(game.game_type)
                self.prev_games[game.channel][game.game_type] = game
            except ValueError as v:
                logger.warn('Gamebase error: %s' % repr(v))
