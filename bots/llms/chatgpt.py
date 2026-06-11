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
