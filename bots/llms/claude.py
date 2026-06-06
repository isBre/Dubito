from bots.base import BotBase
from dubito.game_data import TurnData, honest_times, dishonest_times, doubts_count, turns_count


class ClaudeBot(BotBase):
    """
    Strategy overview
    -----------------
    First hand  — always honest, always maximize: pick_most() dumps all cards
                  of my strongest number and declares that number. No risk,
                  maximum card removal.

    Doubt (C)   — score-based suspicion:
                    50% from prev's historical dishonesty rate
                    50% from how many cards prev played (3 = very suspicious)
                  Threshold adapts to MY card count:
                    few cards (≤4)  → threshold 0.75  (stay conservative, nearly winning)
                    many cards (≥18)→ threshold 0.30  (aggressive, can't get much worse)
                    middle          → threshold 0.50
                  Always doubt if prev has 0 cards (they're winning right now).
                  Slightly lower threshold when I can't play truthfully anyway.

    Bluff (D)   — only when next player's doubt rate is below 35% AND I have
                  fewer matching cards than 3. Why: bluffing plays 3 random
                  cards; honest play dumps only my matching ones. If I have
                  1-2 matches and next won't catch me, bluffing removes more
                  cards. If I have ≥3 matches, honest is equally aggressive
                  with zero risk.

    Maximize    — always. Get rid of cards as fast as possible.
    """

    # --- A: First hand bluff or honest? -----------------------------------

    def bluff_first_hand(self, p: TurnData) -> bool:
        return False

    # --- B: First hand maximize? ------------------------------------------

    def maximize_first_hand(self, p: TurnData) -> bool:
        return True

    # --- C: Doubt or play? ------------------------------------------------

    def should_doubt(self, p: TurnData) -> bool:
        prev_id = p.prev_player_id

        if p.player_card_counts.get(prev_id, 0) == 0:
            return True

        h = honest_times(prev_id, p.history)
        d = dishonest_times(prev_id, p.history)
        total = h + d
        dishonesty_rate = (d / total) if total > 0 else 0.5

        card_suspicion = {1: 0.05, 2: 0.30, 3: 0.65}.get(p.n_cards_played, 0.30)

        if self.prev_player_started_turn(p):
            card_suspicion *= 0.4

        suspicion = 0.5 * dishonesty_rate + 0.5 * card_suspicion

        my_n_cards = len(p.my_cards)
        if my_n_cards <= 4:
            threshold = 0.75
        elif my_n_cards >= 18:
            threshold = 0.30
        else:
            threshold = 0.50

        if suspicion >= threshold:
            return True

        if not self.can_play_truthfully(p):
            return suspicion >= threshold - 0.15

        return False

    # --- D: Bluff or honest? (only called when honest play is possible) ---

    def bluff_regular(self, p: TurnData) -> bool:
        next_id = p.next_player_id
        total_next = turns_count(next_id, p.history)
        next_doubt_rate = (doubts_count(next_id, p.history) / total_next) if total_next > 0 else 0.5

        if next_doubt_rate >= 0.35:
            return False

        return self.cards.count(p.current_number) < 3

    # --- E: Maximize? -----------------------------------------------------

    def maximize_regular(self, p: TurnData) -> bool:
        return True
