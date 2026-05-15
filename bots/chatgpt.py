from bots.base import BotBase
from dubito.game_data import TurnData


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
        total = p.prev.honest_times + p.prev.dishonest_times
        return self._safe_div(p.prev.dishonest_times, total)

    def _next_doubt_rate(self, p: TurnData) -> float:
        return self._safe_div(
            p.next.doubts,
            p.next.not_first_turns,
        )

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

        # Strong opener -> play honestly
        if best_group >= 3:
            return False

        # Very large hand -> aggression helps
        if p.my_n_cards >= 16:
            return True

        # Fragmented hand -> bluffing creates pressure
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

        # If we have a huge honest stack, absolutely dump it
        if best_group >= 3:
            return True

        # Small hand -> avoid overexposing ourselves
        if p.my_n_cards <= 4:
            return False

        return True

    # ---------- C ----------

    def should_doubt(self, p: TurnData) -> bool:
        """
        Core probabilistic doubting logic.
        """

        # Must stop immediate wins
        if p.prev.n_cards == 0:
            return True

        bluff_rate = self._prev_bluff_rate(p)

        # If prev selected the number themselves,
        # they are slightly more trustworthy
        if self.prev_player_started_turn(p):
            bluff_rate -= 0.12

        # More cards played = more suspicious
        bluff_rate += 0.12 * (p.n_cards_played - 1)

        # Long streaks create huge penalties if wrong
        bluff_rate += min(0.18, p.streak * 0.02)

        # If we hold many copies ourselves,
        # it becomes harder for them to be truthful
        mine = self._my_matching(p)

        if mine >= 3:
            bluff_rate += 0.45
        elif mine == 2:
            bluff_rate += 0.22
        elif mine == 1:
            bluff_rate += 0.08

        # Near-endgame players bluff more often
        if p.prev.n_cards <= 3:
            bluff_rate += 0.18

        # Large hands tend to bluff aggressively
        if p.prev.n_cards >= 15:
            bluff_rate += 0.08

        # Very large pile -> avoid reckless doubts
        threshold = 0.72

        if p.board_cards >= 10:
            threshold += 0.08

        if p.board_cards >= 16:
            threshold += 0.08

        # With tiny hand, play safer
        if p.my_n_cards <= 3:
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

        # Huge honest play available -> never bluff
        if matching >= 3:
            return False

        next_doubt = self._next_doubt_rate(p)

        # Endgame: avoid unnecessary risk
        if p.my_n_cards <= 3:
            return False

        # Desperate large-hand aggression
        if p.my_n_cards >= 15 and next_doubt < 0.45:
            return True

        # 1-card honest plays are inefficient
        if matching == 1:
            return next_doubt < 0.38

        # 2-card honest plays are borderline
        if matching == 2:
            return next_doubt < 0.22

        return False

    # ---------- E ----------

    def maximize_regular(self, p: TurnData) -> bool:
        """
        Usually maximize.
        Tempo matters heavily in Dubito.
        """

        # Tiny hand -> reduce risk profile
        if p.my_n_cards <= 3:
            return False

        # Bluffing should usually maximize value
        if not self.can_play_truthfully(p):
            return True

        matching = self._my_matching(p)

        # Big truthful dump is excellent
        if matching >= 2:
            return True

        # If next player doubts a lot,
        # avoid gigantic suspicious bluffs
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
        # Uses the observed honesty/bluff history when available.
        total = p.prev.honest_times + p.prev.dishonest_times
        rate = self._rate(p.prev.dishonest_times, total, default=0.5)

        # Lightly adjust for uncertainty and pressure.
        # Players with very few cards are often under pressure and more likely to bluff.
        if p.prev.n_cards <= 2:
            rate += 0.08
        elif p.prev.n_cards >= 7:
            rate -= 0.03

        # A 3-card play is the most plausible bluff candidate.
        if p.n_cards_played == 3:
            rate += 0.08
        elif p.n_cards_played == 1:
            rate -= 0.03

        # If they opened the turn themselves, slightly reduce suspicion.
        if self.prev_player_started_turn(p):
            rate -= 0.05

        return self._clamp(rate, 0.05, 0.95)

    def _next_doubt_rate(self, p: TurnData) -> float:
        rate = self._rate(p.next.doubts, p.next.not_first_turns, default=0.5)

        # Players close to winning are often more aggressive, but also more willing
        # to challenge a risky play.
        if p.next.n_cards <= 2:
            rate += 0.05
        elif p.next.n_cards >= 8:
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

        # Honest opening is usually strongest. Bluff only on weak, flat hands.
        weak_hand = max_same <= 1
        low_risk_table = next_doubt < 0.30
        crowded_hand = len(self.cards) >= 10

        return bool(weak_hand and low_risk_table and crowded_hand)

    def maximize_first_hand(self, p: TurnData) -> bool:
        return True

    # ---------- regular turns ----------

    def should_doubt(self, p: TurnData) -> bool:
        # Never doubt on an empty board; the framework says this is illegal.
        if p.board_cards == 0:
            return False

        # Immediate stop-the-win cases.
        if p.prev.n_cards == 0:
            return True

        bluff_rate = self._opponent_bluff_rate(p)
        board_pressure = p.board_cards
        streak_pressure = p.streak

        # The bigger the pile, the more expensive a failed doubt becomes.
        # So we need higher confidence as the board grows.
        confidence_needed = 0.56
        if board_pressure >= 7:
            confidence_needed = 0.66
        if board_pressure >= 10:
            confidence_needed = 0.74
        if streak_pressure >= 5:
            confidence_needed += 0.05

        # Strong cases for doubting.
        if p.n_cards_played == 3 and bluff_rate >= confidence_needed - 0.08:
            return True
        if p.prev.n_cards <= 2 and bluff_rate >= confidence_needed:
            return True
        if p.prev.n_cards <= 1 and bluff_rate >= 0.50:
            return True

        # When the previous player is statistically dubious and the board is still small,
        # challenge more often.
        if bluff_rate >= confidence_needed and board_pressure <= 6:
            return True

        # Otherwise play on.
        return False

    def bluff_regular(self, p: TurnData) -> bool:
        """Bluff only when it buys us enough tempo/card advantage.

        Since a truthful play can be better if we already hold many matching cards,
        we avoid bluffing when our match count is strong.
        """
        match_count = self._my_match_count(p)
        next_doubt = self._next_doubt_rate(p)
        board_pressure = p.board_cards

        # If we can truthfully play 3+ cards, honesty is usually best.
        if match_count >= 3:
            return False

        # With 1-2 matching cards, a bluff can remove one extra card.
        # Prefer bluffing only when the next player is relatively passive and
        # the board isn't already too expensive to risk.
        if match_count in (1, 2):
            if next_doubt < 0.42 and board_pressure <= 7:
                return True
            if p.my_n_cards >= 12 and next_doubt < 0.50 and board_pressure <= 5:
                return True
            return False

        # Forced bluff if we do not hold the current number.
        return True

    def maximize_regular(self, p: TurnData) -> bool:
        # Maximizing is generally strong in this game because it improves hand
        # compression and increases the odds of four-of-a-kind discards later.
        return True
