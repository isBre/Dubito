import random
from bots.base import BotBase
from dubito.game_data import TurnData


class BalancedBot(BotBase):
    """
    Mixes honest play, bluffing, and doubting with calibrated probabilities:
    - bluffs 67% of the time
    - doubt threshold scales with cards played (30/60/90%), skipped when prev opened the round
    - always maximises card removal
    """

    _DOUBT_THRESHOLDS = {1: 0.3, 2: 0.6, 3: 0.9}

    def bluff_first_hand(self, p: TurnData) -> bool:    return random.random() < 0.67
    def maximize_first_hand(self, p: TurnData) -> bool: return True

    def should_doubt(self, p: TurnData) -> bool:
        if self.prev_player_started_turn(p):
            return False
        if p.player_card_counts.get(p.prev_player_id, 0) == 0:
            return True
        threshold = self._DOUBT_THRESHOLDS.get(p.n_cards_played, 0)
        return random.random() < threshold

    def bluff_regular(self, p: TurnData) -> bool:       return random.random() < 0.67
    def maximize_regular(self, p: TurnData) -> bool:    return True
