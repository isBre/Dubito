from bots.base import BotBase
from dubito.game_data import TurnData, honest_times, dishonest_times, doubts_count, turns_count


class ChatGPTThinkingBot(BotBase):
    """A risk-aware bot that favours honest play and doubts only on strong evidence.

    Strategy:
    - Play honestly by default and always maximise card removal.
    - Doubt only when the expected value is clearly favourable.
    - Bluff mainly when the next player is unlikely to challenge and the
      bluff meaningfully increases card removal.
    """

    # ---------- helpers ----------

    @staticmethod
    def _rate(numer: int, denom: int, default: float = 0.5) -> float:
        return default if denom <= 0 else numer / denom

    @classmethod
    def _clamp(cls, x: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, x))

    def _opponent_bluff_rate(self, p: TurnData) -> float:
        prev_id = p.prev_player_id
        h = honest_times(prev_id, p.history)
        d = dishonest_times(prev_id, p.history)
        rate = self._rate(d, h + d, default=0.5)

        prev_cards = p.player_card_counts.get(prev_id, 0)
        if prev_cards <= 2:
            rate += 0.08
        elif prev_cards >= 7:
            rate -= 0.03

        if p.n_cards_played == 3:
            rate += 0.08
        elif p.n_cards_played == 1:
            rate -= 0.03

        if self.prev_player_started_turn(p):
            rate -= 0.05

        return self._clamp(rate, 0.05, 0.95)

    def _next_doubt_rate(self, p: TurnData) -> float:
        next_id = p.next_player_id
        rate = self._rate(doubts_count(next_id, p.history), turns_count(next_id, p.history), default=0.5)

        next_cards = p.player_card_counts.get(next_id, 0)
        if next_cards <= 2:
            rate += 0.05
        elif next_cards >= 8:
            rate -= 0.03

        return self._clamp(rate, 0.05, 0.95)

    def _my_match_count(self, p: TurnData) -> int:
        return self.cards.count(p.current_number)

    # ---------- A: first hand ----------

    def bluff_first_hand(self, p: TurnData) -> bool:
        """Bluff only when the hand is weak and the table is passive."""
        next_doubt = self._next_doubt_rate(p)
        cnts = self.cards.count_all()
        max_same = max(cnts.values()) if cnts else 0

        weak_hand = max_same <= 1
        low_risk_table = next_doubt < 0.30
        crowded_hand = len(self.cards) >= 10

        return bool(weak_hand and low_risk_table and crowded_hand)

    def maximize_first_hand(self, p: TurnData) -> bool:
        return True

    # ---------- C: doubt or play ----------

    def should_doubt(self, p: TurnData) -> bool:
        if p.board_cards == 0:
            return False

        prev_id = p.prev_player_id
        if p.player_card_counts.get(prev_id, 0) == 0:
            return True

        bluff_rate = self._opponent_bluff_rate(p)
        board_pressure = p.board_cards
        streak_pressure = p.streak

        confidence_needed = 0.56
        if board_pressure >= 7:
            confidence_needed = 0.66
        if board_pressure >= 10:
            confidence_needed = 0.74
        if streak_pressure >= 5:
            confidence_needed += 0.05

        prev_cards = p.player_card_counts.get(prev_id, 0)
        if p.n_cards_played == 3 and bluff_rate >= confidence_needed - 0.08:
            return True
        if prev_cards <= 2 and bluff_rate >= confidence_needed:
            return True
        if prev_cards <= 1 and bluff_rate >= 0.50:
            return True

        if bluff_rate >= confidence_needed and board_pressure <= 6:
            return True

        return False

    # ---------- D: bluff or honest ----------

    def bluff_regular(self, p: TurnData) -> bool:
        """Bluff only when it buys meaningful tempo or card-removal advantage."""
        match_count = self._my_match_count(p)
        next_doubt = self._next_doubt_rate(p)
        board_pressure = p.board_cards

        if match_count >= 3:
            return False

        if match_count in (1, 2):
            if next_doubt < 0.42 and board_pressure <= 7:
                return True
            if len(p.my_cards) >= 12 and next_doubt < 0.50 and board_pressure <= 5:
                return True
            return False

        return True

    # ---------- E: maximize ----------

    def maximize_regular(self, p: TurnData) -> bool:
        return True
