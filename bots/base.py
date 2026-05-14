from abc import abstractmethod
from typing import Dict
from player import PlayerAI


class BotBase(PlayerAI):
    """
    Structured abstract base for all bots.

    Maps directly to the 5 decision points of the game tree:

        MY TURN
        │
        ├─ First hand?
        │   ├─ YES ──► [A] bluff_first_hand   — bluff or honest?
        │   │           [B] maximize_first_hand — how many cards?
        │   │
        │   └─ NO ───► [C] should_doubt        — doubt or play?
        │               │
        │               └─ if Play
        │                   [D] bluff_regular   — bluff or honest?  (only when honest is possible)
        │                   [E] maximize_regular — how many cards?

    Subclasses implement only A–E. The framework enforces game rules
    (e.g. forced bluff when the current number is not in hand) and
    assembles the final output dict.
    """

    # ------------------------------------------------------------------
    # A — First hand: bluff or honest?
    # ------------------------------------------------------------------
    @abstractmethod
    def bluff_first_hand(self, input_player: Dict) -> bool:
        """Return True to bluff, False to play honestly."""

    # ------------------------------------------------------------------
    # B — First hand: maximize cards played?
    # ------------------------------------------------------------------
    @abstractmethod
    def maximize_first_hand(self, input_player: Dict) -> bool:
        """Return True to play as many cards as possible, False for a random amount (1–3)."""

    # ------------------------------------------------------------------
    # C — Regular turn: doubt or play?
    # ------------------------------------------------------------------
    @abstractmethod
    def should_doubt(self, input_player: Dict) -> bool:
        """Return True to challenge the previous player, False to play cards."""

    # ------------------------------------------------------------------
    # D — Regular turn: bluff or honest?
    #     Only called when can_play_truthfully() is True.
    #     When the current number is not in hand, bluff is forced by the rules.
    # ------------------------------------------------------------------
    @abstractmethod
    def bluff_regular(self, input_player: Dict) -> bool:
        """Return True to bluff, False to play honestly. Only called when honest play is possible."""

    # ------------------------------------------------------------------
    # E — Regular turn: maximize cards played?
    # ------------------------------------------------------------------
    @abstractmethod
    def maximize_regular(self, input_player: Dict) -> bool:
        """Return True to play as many cards as possible, False for a random amount (1–3)."""

    # ------------------------------------------------------------------
    # Framework — wires A–E into the PlayerAI protocol
    # ------------------------------------------------------------------

    def play_first_turn(self, input_player: Dict) -> Dict:
        maximize = self.maximize_first_hand(input_player)       # B
        if self.bluff_first_hand(input_player):                 # A
            return self.bluff(input_player, first_turn=True, uncertainty=False, maximize=maximize)
        return self.play_truthfully(input_player, first_turn=True, uncertainty=False, maximize=maximize)

    def play_regular_turn(self, input_player: Dict) -> Dict:
        if self.should_doubt(input_player):                     # C
            return self.doubt(input_player, uncertainty=False)
        maximize = self.maximize_regular(input_player)          # E
        if self.can_play_truthfully(input_player) and not self.bluff_regular(input_player):  # D
            return self.play_truthfully(input_player, first_turn=False, uncertainty=False, maximize=maximize)
        return self.bluff(input_player, first_turn=False, uncertainty=False, maximize=maximize)
