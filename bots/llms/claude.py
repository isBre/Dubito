from bots.base import BotBase
from dubito.game_data import TurnData


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
        return False  # always pick the number we're strongest in

    # --- B: First hand maximize? ------------------------------------------

    def maximize_first_hand(self, p: TurnData) -> bool:
        return True

    # --- C: Doubt or play? ------------------------------------------------

    def should_doubt(self, p: TurnData) -> bool:
        # Prev is about to win — stop them at any cost
        if p.prev.n_cards == 0:
            return True

        # Historical dishonesty rate of prev
        total = p.prev.honest_times + p.prev.dishonest_times
        dishonesty_rate = (p.prev.dishonest_times / total) if total > 0 else 0.5

        # Cards played: more cards = harder to have legitimately
        card_suspicion = {1: 0.05, 2: 0.30, 3: 0.65}.get(p.n_cards_played, 0.30)

        # Prev started the round → they chose the number, more likely honest
        if self.prev_player_started_turn(p):
            card_suspicion *= 0.4

        suspicion = 0.5 * dishonesty_rate + 0.5 * card_suspicion

        # Adapt threshold to my card count
        if p.my_n_cards <= 4:
            threshold = 0.75   # nearly winning — stay safe
        elif p.my_n_cards >= 18:
            threshold = 0.30   # drowning in cards — be aggressive
        else:
            threshold = 0.50

        if suspicion >= threshold:
            return True

        # Can't play truthfully anyway → lower the bar slightly before bluffing
        if not self.can_play_truthfully(p):
            return suspicion >= threshold - 0.15

        return False

    # --- D: Bluff or honest? (only called when honest play is possible) ---

    def bluff_regular(self, p: TurnData) -> bool:
        # Check how often next player doubts
        total_next = p.next.not_first_turns
        next_doubt_rate = (p.next.doubts / total_next) if total_next > 0 else 0.5

        # Only bluff if next player rarely doubts
        if next_doubt_rate >= 0.35:
            return False

        # Bluff is only worth it if I have fewer matching cards than 3.
        # Bluffing plays 3 random cards; honest plays all matching ones.
        # If matching >= 3, honest removes at least as many cards with no risk.
        return self.cards.count(p.current_number) < 3

    # --- E: Maximize? -----------------------------------------------------

    def maximize_regular(self, p: TurnData) -> bool:
        return True
