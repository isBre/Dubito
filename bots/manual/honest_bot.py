from bots.base import BotBase
from dubito.game_data import TurnData


class HonestBot(BotBase):
    """Plays honestly whenever possible; doubts only when it cannot play truthfully."""

    def bluff_first_hand(self, p: TurnData) -> bool:    return False
    def maximize_first_hand(self, p: TurnData) -> bool: return True
    def should_doubt(self, p: TurnData) -> bool:        return not self.can_play_truthfully(p)
    def bluff_regular(self, p: TurnData) -> bool:       return False
    def maximize_regular(self, p: TurnData) -> bool:    return True
