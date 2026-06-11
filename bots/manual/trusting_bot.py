from bots.base import BotBase
from dubito.game_data import TurnData


class TrustingBot(BotBase):
    """Never doubts; plays honestly when possible, bluffs otherwise."""

    def bluff_first_hand(self, p: TurnData) -> bool:    return False
    def maximize_first_hand(self, p: TurnData) -> bool: return True
    def should_doubt(self, p: TurnData) -> bool:        return False
    def bluff_regular(self, p: TurnData) -> bool:       return False
    def maximize_regular(self, p: TurnData) -> bool:    return True
