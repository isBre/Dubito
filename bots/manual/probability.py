import random
from bots.base import BotBase
from dubito.game_data import TurnData, honest_times, dishonest_times, doubts_count, turns_count


class AdaptyBoi(BotBase):
    """Adapts play based on the observed honesty of prev and doubt frequency of next."""

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


class SusBoi(BotBase):
    """Doubts with increasing probability the more cards prev played; honest otherwise."""

    _DOUBT_THRESHOLDS = {1: 0.3, 2: 0.6, 3: 0.9}

    def bluff_first_hand(self, p: TurnData) -> bool:   return False
    def maximize_first_hand(self, p: TurnData) -> bool: return True

    def should_doubt(self, p: TurnData) -> bool:
        threshold = self._DOUBT_THRESHOLDS.get(p.n_cards_played, 0)
        if random.random() < threshold:
            return True
        return not self.can_play_truthfully(p)

    def bluff_regular(self, p: TurnData) -> bool:       return False
    def maximize_regular(self, p: TurnData) -> bool:    return True


class UsualBot(BotBase):
    """Doubts based on cards played; skips doubt when prev started the round; bluffs 67%."""

    _DOUBT_THRESHOLDS = {1: 0.3, 2: 0.6, 3: 0.9}

    def bluff_first_hand(self, p: TurnData) -> bool:   return random.random() < 0.67
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


class RiskCounter(BotBase):
    """Aggressive at low risk (bluffs), conservative at high risk (honest or doubts)."""

    def __init__(self, id: int) -> None:
        super().__init__(id)
        self.risk = 0.01

    def play(self, input_player: TurnData) -> dict:
        self._update_risk(input_player, first_turn=self.is_first_turn(input_player))
        return super().play(input_player)

    def bluff_first_hand(self, p: TurnData) -> bool:   return random.random() < self.risk
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
                self.risk = max(0, min(0.99, -(1/30) * next_cards**2 + 1))
        else:
            self.risk = max(0, min(0.99, (1/40) * p.board_cards**2))
