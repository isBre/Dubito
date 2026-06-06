from bots.base import BotBase
from dubito.game_data import TurnData, honest_times, dishonest_times, doubts_count, turns_count


class ChatGPTBot(BotBase):
    """
    Aggressive probabilistic bot focused on:
    - Fast hand reduction
    - Smart bluff timing
    - Punishing obvious lies
    - Endgame denial
    - Exploiting low-doubt opponents
    """

    def __init__(self, id: int) -> None:
        super().__init__(id)

    # ---------- Helpers ----------

    def _safe_div(self, a: float, b: float, default: float = 0.5) -> float:
        return a / b if b else default

    def _prev_bluff_rate(self, p: TurnData) -> float:
        prev_id = p.prev_player_id
        h = honest_times(prev_id, p.history)
        d = dishonest_times(prev_id, p.history)
        return self._safe_div(d, h + d)

    def _next_doubt_rate(self, p: TurnData) -> float:
        next_id = p.next_player_id
        return self._safe_div(doubts_count(next_id, p.history), turns_count(next_id, p.history))

    def _my_matching(self, p: TurnData) -> int:
        return self.cards.count(p.current_number)

    # ---------- A ----------

    def bluff_first_hand(self, p: TurnData) -> bool:
        """
        Bluff first hand only when:
        - our hand is weak / fragmented
        - or we are very card-heavy and need tempo
        """

        counts = self.cards.count_all()

        if not counts:
            return False

        best_group = max(counts.values())

        if best_group >= 3:
            return False

        my_n_cards = len(p.my_cards)
        if my_n_cards >= 16:
            return True

        if best_group == 1:
            return True

        return False

    # ---------- B ----------

    def maximize_first_hand(self, p: TurnData) -> bool:
        """
        Usually maximize.
        Dumping cards early is extremely valuable.
        """

        counts = self.cards.count_all()

        if not counts:
            return True

        best_group = max(counts.values())

        if best_group >= 3:
            return True

        if len(p.my_cards) <= 4:
            return False

        return True

    # ---------- C ----------

    def should_doubt(self, p: TurnData) -> bool:
        """
        Core probabilistic doubting logic.
        """

        prev_id = p.prev_player_id
        if p.player_card_counts.get(prev_id, 0) == 0:
            return True

        bluff_rate = self._prev_bluff_rate(p)

        if self.prev_player_started_turn(p):
            bluff_rate -= 0.12

        bluff_rate += 0.12 * (p.n_cards_played - 1)
        bluff_rate += min(0.18, p.streak * 0.02)

        mine = self._my_matching(p)
        if mine >= 3:
            bluff_rate += 0.45
        elif mine == 2:
            bluff_rate += 0.22
        elif mine == 1:
            bluff_rate += 0.08

        prev_cards = p.player_card_counts.get(prev_id, 0)
        if prev_cards <= 3:
            bluff_rate += 0.18
        if prev_cards >= 15:
            bluff_rate += 0.08

        threshold = 0.72
        if p.board_cards >= 10:
            threshold += 0.08
        if p.board_cards >= 16:
            threshold += 0.08
        if len(p.my_cards) <= 3:
            threshold += 0.08

        return bluff_rate >= threshold

    # ---------- D ----------

    def bluff_regular(self, p: TurnData) -> bool:
        """
        Bluff selectively when:
        - honest play is weak
        - next player rarely doubts
        - we need tempo
        """

        matching = self._my_matching(p)

        if matching >= 3:
            return False

        next_doubt = self._next_doubt_rate(p)
        my_n_cards = len(p.my_cards)

        if my_n_cards <= 3:
            return False

        if my_n_cards >= 15 and next_doubt < 0.45:
            return True

        if matching == 1:
            return next_doubt < 0.38

        if matching == 2:
            return next_doubt < 0.22

        return False

    # ---------- E ----------

    def maximize_regular(self, p: TurnData) -> bool:
        """
        Usually maximize.
        Tempo matters heavily in Dubito.
        """

        if len(p.my_cards) <= 3:
            return False

        if not self.can_play_truthfully(p):
            return True

        matching = self._my_matching(p)

        if matching >= 2:
            return True

        next_doubt = self._next_doubt_rate(p)
        if next_doubt >= 0.65:
            return False

        return True


class ChatGPT_thinking(BotBase):
    """A risk-aware Dubito bot.

    Strategy:
    - Play honestly by default.
    - Maximize card removal whenever possible.
    - Doubt only when the expected value is clearly favorable.
    - Bluff mainly when the next player is unlikely to challenge us and the
      bluff meaningfully increases card removal.
    """

    # ---------- small helpers ----------

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

    # ---------- first hand ----------

    def bluff_first_hand(self, p: TurnData) -> bool:
        """Usually play honestly on the opening hand.

        We only open with a bluff when:
        - our hand is awkward (no duplicates to capitalize on), and
        - the next player is unlikely to challenge.
        """
        next_doubt = self._next_doubt_rate(p)
        cnts = self.cards.count_all()
        max_same = max(cnts.values()) if cnts else 0

        weak_hand = max_same <= 1
        low_risk_table = next_doubt < 0.30
        crowded_hand = len(self.cards) >= 10

        return bool(weak_hand and low_risk_table and crowded_hand)

    def maximize_first_hand(self, p: TurnData) -> bool:
        return True

    # ---------- regular turns ----------

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

    def bluff_regular(self, p: TurnData) -> bool:
        """Bluff only when it buys us enough tempo/card advantage."""
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

    def maximize_regular(self, p: TurnData) -> bool:
        return True
