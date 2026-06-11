import random
from bots.base import BotBase
from dubito.game_data import TurnData, honest_times, dishonest_times, doubts_count, turns_count


class AdaptiveBot(BotBase):
    """
    Adapts bluffing and doubting thresholds based on observed opponent behaviour:
    - tracks the previous player's honesty rate to calibrate doubt decisions
    - tracks the next player's doubt rate to calibrate bluff decisions
    """

    def __init__(self, id: int) -> None:
        super().__init__(id)
        self.prev_honesty_prob = 0.5  # higher → prev tends to be honest
        self.next_doubt_prob = 0.5    # higher → next tends to doubt a lot

    def play(self, input_player: TurnData) -> dict:
        self._update(input_player)
        return super().play(input_player)

    def bluff_first_hand(self, p: TurnData) -> bool:
        return random.random() >= self.next_doubt_prob

    def maximize_first_hand(self, p: TurnData) -> bool: return True

    def should_doubt(self, p: TurnData) -> bool:
        if random.random() >= self.prev_honesty_prob:
            return True
        if random.random() < self.next_doubt_prob and not self.can_play_truthfully(p):
            return self.prev_honesty_prob <= self.next_doubt_prob
        return False

    def bluff_regular(self, p: TurnData) -> bool:
        return random.random() >= self.next_doubt_prob

    def maximize_regular(self, p: TurnData) -> bool: return True

    def _update(self, p: TurnData) -> None:
        prev_id = p.prev_player_id
        h = honest_times(prev_id, p.history)
        d = dishonest_times(prev_id, p.history)
        total = h + d
        if total > 0:
            ratio = h / total
            self.prev_honesty_prob = min(1 - self.uncertainty_value, max(self.uncertainty_value, ratio))

        next_id = p.next_player_id
        next_turns = turns_count(next_id, p.history)
        if next_turns > 0:
            ratio = doubts_count(next_id, p.history) / next_turns
            self.next_doubt_prob = min(1 - self.uncertainty_value, max(self.uncertainty_value, ratio))
