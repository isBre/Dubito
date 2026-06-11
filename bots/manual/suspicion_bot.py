import random
from bots.base import BotBase
from dubito.game_data import TurnData


class SuspicionBot(BotBase):
    """
    Doubt probability scales with the number of cards the previous player put down:
    1 card → 30%, 2 cards → 60%, 3 cards → 90%.
    Plays honestly otherwise.
    """

    _DOUBT_THRESHOLDS = {1: 0.3, 2: 0.6, 3: 0.9}

    def bluff_first_hand(self, p: TurnData) -> bool:    return False
    def maximize_first_hand(self, p: TurnData) -> bool: return True

    def should_doubt(self, p: TurnData) -> bool:
        threshold = self._DOUBT_THRESHOLDS.get(p.n_cards_played, 0)
        if random.random() < threshold:
            return True
        return not self.can_play_truthfully(p)

    def bluff_regular(self, p: TurnData) -> bool:       return False
    def maximize_regular(self, p: TurnData) -> bool:    return True
