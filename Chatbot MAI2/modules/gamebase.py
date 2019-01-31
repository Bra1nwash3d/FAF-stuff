import persistent.dict
import transaction
from modules.utils import get_logger, get_lock, time_to_str
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
        self.current_games = persistent.dict.PersistentDict()   # current games
        self.prev_games = persistent.dict.PersistentDict()      # previous games, e.g. to reveal cards after the game
        self.eventbase = eventbase
        self.effectbase = effectbase
        self.chatbase = chatbase
        self.spam_protect = spam_protect
        self.queue = queue
        self.game_cooldowns = {}
        self.default_game_cooldown = 30
        self.default_roulette_duration = 60
        self.save()
        logger.info('Created new Gamebase')

    def set(self, eventbase: Eventbase, queue: CallbackQueue, chatbase: Chatbase, effectbase: EffectBase,
            spam_protect: SpamProtect):
        self.eventbase = eventbase
        self.effectbase = effectbase
        self.chatbase = chatbase
        self.spam_protect = spam_protect
        self.queue = queue

    def reset(self):
        with lock:
            for game in self.current_games.values():
                game.reset()
            self.current_games.clear()
            self.save()
            logger.info('Reset Gamebase')

    def update_vars(self, game_cooldowns=None, default_game_cooldown=None, default_roulette_duration=None, **_):
        with lock:
            # function to set misc vars
            self.default_game_cooldown = \
                default_game_cooldown if default_game_cooldown is not None else self.default_game_cooldown
            self.default_roulette_duration =\
                default_roulette_duration if default_roulette_duration is not None else self.default_roulette_duration
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

    def __get_game(self, channel: str, game_type: GameType, prev=False) -> Game:
        """ returns None if there is no current game, an exception if there is another game or games are disabled,
            and the game itself if there is an active game with the correct type """
        with lock:
            if not self.chatbase.is_accepted_for_games(channel) and not prev:
                raise ValueError('Games are not enabled in channel %s!' % channel)
            if prev:
                if self.prev_games.get(channel, None) is None:
                    self.prev_games[channel] = {}
                game = self.prev_games.get(channel).get(game_type, None)
            else:
                game = self.current_games.get(channel)
            if game is None:
                return game
            if game.game_type == game_type:
                return game
            raise ValueError('Another game is already running in channel %s!' % channel)

    def get_roulette_game(self, chat_type: ChatType, channel: str, requested_by: str) -> RouletteGame:
        with lock:
            game = self.__get_game(channel, GameType.ROULETTE)
            if game is None:
                self.spam_protect.print()
                is_spam, rem_time = self.spam_protect.is_spam(channel, GameType.ROULETTE.value)
                if is_spam:
                    raise ValueError('Roulette is on cooldown, please wait %s.' % time_to_str(rem_time))
                game = RouletteGame(chat_type, channel, requested_by, self.queue, self.remove_game, self.chatbase,
                                    self.eventbase, self.default_roulette_duration)
                self.current_games[channel] = game
            return game

    def remove_game(self, game: Game):
        """ callback for games that ended """
        logger.info('remove game: %s' % game.game_type)
        with lock:
            if game is None:
                return
            try:
                cur_game = self.current_games.pop(game.channel)
                if cur_game.ended() and game == cur_game:
                    self.__get_game(game.channel, game.game_type, prev=True)  # just to create the dict structure
                    self.prev_games[game.channel][game.game_type] = game
                else:
                    self.current_games[cur_game.channel] = cur_game
                self.spam_protect.set_now(game.channel, game.game_type.value)
            except Exception as v:
                logger.warn('Gamebase error: %s' % repr(v))
