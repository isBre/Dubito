import random
from bots.base import BotBase
from dubito.game_data import TurnData


class AlwaysDoubtBot(BotBase):
    """Always doubts on regular turns; plays randomly on the opening hand."""

    def bluff_first_hand(self, p: TurnData) -> bool:    return random.choice([True, False])
    def maximize_first_hand(self, p: TurnData) -> bool: return True
    def should_doubt(self, p: TurnData) -> bool:        return True
    def bluff_regular(self, p: TurnData) -> bool:       return True   # unreachable
    def maximize_regular(self, p: TurnData) -> bool:    return True   # unreachable
