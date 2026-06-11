import random
from bots.base import BotBase
from dubito.game_data import TurnData


class RandomBot(BotBase):
    """Makes all decisions uniformly at random."""

    def bluff_first_hand(self, p: TurnData) -> bool:    return random.choice([True, False])
    def maximize_first_hand(self, p: TurnData) -> bool: return False

    def should_doubt(self, p: TurnData) -> bool:
        if self.can_play_truthfully(p):
            return random.random() < 1 / 3  # 1-in-3 chance: bluff / honest / doubt
        return random.choice([True, False])  # 50/50: doubt or bluff

    def bluff_regular(self, p: TurnData) -> bool:       return random.choice([True, False])
    def maximize_regular(self, p: TurnData) -> bool:    return False
