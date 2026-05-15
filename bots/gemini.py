from bots.base import BotBase
from dubito.game_data import TurnData


class GeminiBot(BotBase):
    """
    GeminiBot: A strategy focused on card counting and risk-reward ratios.
    - Uses card counts to identify impossible plays.
    - Calculates doubt probability based on opponent history.
    - Aggressively dumps cards when the next player is passive.
    """

    def bluff_first_hand(self, p: TurnData) -> bool:
        # We only bluff the opening if our hand is absolute garbage (all singles).
        # Otherwise, playing honestly helps us build toward a 4-of-a-kind discard.
        counts = self.cards.count_all()
        if max(counts.values(), default=0) >= 2:
            return False
        return True

    def maximize_first_hand(self, p: TurnData) -> bool:
        # Always try to get rid of as many cards as possible early on.
        return True

    def should_doubt(self, p: TurnData) -> bool:
        # 1. CRITICAL: Prev player is about to win.
        if p.prev.n_cards == 0:
            return True

        # 2. MATHEMATICAL CERTAINTY:
        # There are only 4 of any card. If (My Count + Played) > 4, they are bluffing.
        # (Jokers exist, but the odds still heavily favor a bluff).
        my_count = self.cards.count(p.current_number)
        if my_count + p.n_cards_played > 4:
            return True

        # 3. STATISTICAL SUSPICION:
        # Calculate opponent's bluff rate. Assume 50% if no data.
        total_caught = p.prev.honest_times + p.prev.dishonest_times
        bluff_rate = p.prev.dishonest_times / total_caught if total_caught > 0 else 0.5

        # 4. RISK ASSESSMENT:
        # If the board is huge (streak > 5 or board_cards > 10), be very conservative.
        # If the board is small, be a "police officer" to keep others from emptying hands.
        risk_threshold = 0.8 if p.board_cards < 5 else 0.4

        # Doubt if they are a known liar and the risk is acceptable.
        if bluff_rate > risk_threshold:
            return True

        # 5. INTUITION:
        # Playing 3 cards is statistically harder than playing 1.
        if p.n_cards_played == 3 and my_count >= 2:
            return True

        return False

    def bluff_regular(self, p: TurnData) -> bool:
        # If we don't have the card, the framework forces a bluff anyway.
        if not self.can_play_truthfully(p):
            return True

        # If we have the card, should we bluff to dump MORE?
        my_count = self.cards.count(p.current_number)

        # If we can play 3 honestly, do it! (No risk, max reward).
        if my_count >= 3:
            return False

        # If we only have 1, bluffing 3 is tempting.
        # Check if the next player is "Doubt-Happy".
        next_doubt_rate = p.next.doubts / p.next.not_first_turns if p.next.not_first_turns > 0 else 0.5

        # Bluff 3 cards only if the next player is passive and the board is small.
        if my_count == 1 and next_doubt_rate < 0.3 and p.board_cards < 4:
            return True

        return False

    def maximize_regular(self, p: TurnData) -> bool:
        # In Dubito, the fastest way to 0 is to play 3 cards every time.
        # We only play conservatively (1 card) if the next player is a doubt-stalker.
        next_doubt_rate = p.next.doubts / p.next.not_first_turns if p.next.not_first_turns > 0 else 0.5

        if next_doubt_rate > 0.7 and p.board_cards > 6:
            return False  # Play small to avoid being a target for a big board take

        return True