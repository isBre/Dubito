import random
from bots.base import BotBase
from dubito.game_data import TurnData


class RiskAwareBot(BotBase):
    """
    Tracks a risk level and inverts strategy based on it:
    - low risk  → bluffs aggressively
    - high risk → plays honestly and doubts cautiously
    Risk is computed from board state and the next player's card count.
    """

    def __init__(self, id: int) -> None:
        super().__init__(id)
        self.risk = 0.01

    def play(self, input_player: TurnData) -> dict:
        self._update_risk(input_player, first_turn=self.is_first_turn(input_player))
        return super().play(input_player)

    def bluff_first_hand(self, p: TurnData) -> bool:    return random.random() < self.risk
    def maximize_first_hand(self, p: TurnData) -> bool: return True

    def should_doubt(self, p: TurnData) -> bool:
        if p.player_card_counts.get(p.prev_player_id, 0) == 0:
            return True
        return random.random() >= self.risk and not self.can_play_truthfully(p)

    def bluff_regular(self, p: TurnData) -> bool:       return random.random() < self.risk
    def maximize_regular(self, p: TurnData) -> bool:    return True

    def _update_risk(self, p: TurnData, first_turn: bool) -> None:
        if first_turn:
            if self.all_equal():
                self.risk = 1.0
            else:
                next_cards = p.player_card_counts.get(p.next_player_id, 0)
                self.risk = max(0, min(0.99, -(1 / 30) * next_cards ** 2 + 1))
        else:
            self.risk = max(0, min(0.99, (1 / 40) * p.board_cards ** 2))
