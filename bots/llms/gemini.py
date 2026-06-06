from bots.base import BotBase
from dubito.game_data import TurnData, dishonest_times, honest_times, doubts_count, turns_count


class GeminiBot(BotBase):
    """
    GeminiBot: A strategy focused on card counting and risk-reward ratios.
    - Uses card counts to identify impossible plays.
    - Calculates doubt probability based on opponent history.
    - Aggressively dumps cards when the next player is passive.
    """

    def bluff_first_hand(self, p: TurnData) -> bool:
        counts = self.cards.count_all()
        if max(counts.values(), default=0) >= 2:
            return False
        return True

    def maximize_first_hand(self, p: TurnData) -> bool:
        return True

    def should_doubt(self, p: TurnData) -> bool:
        prev_id = p.prev_player_id

        if p.player_card_counts.get(prev_id, 0) == 0:
            return True

        my_count = self.cards.count(p.current_number)
        if my_count + p.n_cards_played > 4:
            return True

        h = honest_times(prev_id, p.history)
        d = dishonest_times(prev_id, p.history)
        total_caught = h + d
        bluff_rate = d / total_caught if total_caught > 0 else 0.5

        risk_threshold = 0.8 if p.board_cards < 5 else 0.4
        if bluff_rate > risk_threshold:
            return True

        if p.n_cards_played == 3 and my_count >= 2:
            return True

        return False

    def bluff_regular(self, p: TurnData) -> bool:
        if not self.can_play_truthfully(p):
            return True

        my_count = self.cards.count(p.current_number)

        if my_count >= 3:
            return False

        next_id = p.next_player_id
        total_next = turns_count(next_id, p.history)
        next_doubt_rate = doubts_count(next_id, p.history) / total_next if total_next > 0 else 0.5

        if my_count == 1 and next_doubt_rate < 0.3 and p.board_cards < 4:
            return True

        return False

    def maximize_regular(self, p: TurnData) -> bool:
        next_id = p.next_player_id
        total_next = turns_count(next_id, p.history)
        next_doubt_rate = doubts_count(next_id, p.history) / total_next if total_next > 0 else 0.5

        if next_doubt_rate > 0.7 and p.board_cards > 6:
            return False

        return True
