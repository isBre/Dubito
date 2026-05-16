"""
RLBot — wraps a trained SB3 model as a tournament-ready BotBase subclass.

Usage:
    from rl.bot import RLBot
    bot = RLBot.load("rl/models/ppo_dubito.zip")
    # add to experiments.py ALL_BOTS dict like any other bot
"""

import os
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import VecNormalize, DummyVecEnv

from bots.base import BotBase
from dubito.game_data import TurnData
from rl.env import build_obs, action_to_output, DubitoEnv

_DEFAULT_MODEL = "rl/models/ppo_dubito.zip"
_DEFAULT_STATS = "rl/models/vecnormalize.pkl"


class RLBot(BotBase):
    """BotBase subclass that delegates all decisions to a trained PPO model."""

    _model:    PPO         | None = None
    _vec_norm: VecNormalize | None = None

    def __init__(
        self,
        player_id: int,
        model_path: str = _DEFAULT_MODEL,
        stats_path: str = _DEFAULT_STATS,
    ):
        super().__init__(player_id)
        if RLBot._model is None:
            RLBot._model = PPO.load(model_path)
            if os.path.exists(stats_path):
                dummy = DummyVecEnv([lambda: DubitoEnv()])
                RLBot._vec_norm = VecNormalize.load(stats_path, dummy)
                RLBot._vec_norm.training = False   # freeze stats at inference time

    @classmethod
    def load(cls, model_path: str, stats_path: str | None = None) -> type:
        """Return a class pre-loaded with specific model/stats paths."""
        sp = stats_path or model_path.replace(".zip", "_vecnormalize.pkl").replace(
            "ppo_dubito", "vecnormalize"
        )
        class _Loaded(cls):
            def __init__(self, pid):
                super().__init__(pid, model_path=model_path, stats_path=sp)
        _Loaded.__name__     = "RLBot"
        _Loaded.__qualname__ = "RLBot"
        return _Loaded

    def play(self, input_player: TurnData):
        is_first = input_player.board_cards == 0
        obs = build_obs(input_player, list(self.cards.hand), jokers_in_last_play=False)

        # Apply the same normalisation that was used during training
        if self._vec_norm is not None:
            obs = self._vec_norm.normalize_obs(obs)

        action, _ = self._model.predict(obs, deterministic=True)
        return action_to_output(int(action), self, input_player, is_first)

    # BotBase abstract methods — never reached (we override play() directly)
    def bluff_first_hand(self, p):    return True
    def maximize_first_hand(self, p): return False
    def should_doubt(self, p):        return False
    def bluff_regular(self, p):       return True
    def maximize_regular(self, p):    return False
