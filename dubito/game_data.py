from __future__ import annotations
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Game events — emitted after each action and stored in game_handler.history.
# Only observable information is included (card values are hidden until doubted).
# ---------------------------------------------------------------------------

@dataclass
class GameStartEvent:
    player_ids: list[int]               # in turn order
    initial_card_counts: dict[int, int] # player_id → starting n_cards


@dataclass
class CardsPlayedEvent:
    player_id: int
    declared_number: int
    n_cards: int


@dataclass
class DoubtResolvedEvent:
    doubter_id: int
    target_id: int
    correct: bool           # True = bluffer caught; False = doubter wrong
    latest_cards: list[int] # target's actual last play (now revealed)
    board_cards: list[int]  # cards the loser picks up
    declared_number: int
    jokers_discarded: int = 0

    @property
    def loser_id(self) -> int:
        return self.target_id if self.correct else self.doubter_id


@dataclass
class DiscardEvent:
    player_id: int
    card_number: int        # 4 of this number were removed from their hand


@dataclass
class PlayerWonEvent:
    player_id: int
    position: int           # 1 = first place, 2 = second, etc.


GameEvent = GameStartEvent | CardsPlayedEvent | DoubtResolvedEvent | DiscardEvent | PlayerWonEvent


# ---------------------------------------------------------------------------
# Turn data — the single input to player.play() each turn.
#
# Certain fields are engine-verified facts (the game knows these for sure).
# history contains the raw event log: derive anything uncertain from it
# (bluff rates, revealed cards, behavioural patterns, etc.).
# ---------------------------------------------------------------------------

@dataclass
class TurnData:
    # — Certain current snapshot —
    my_cards: list[int]                 # my own hand (private to me)
    current_number: int                 # declared number this round (0 on first hand)
    board_cards: int                    # total cards on the board
    n_cards_played: int                 # how many cards prev player just placed
    playing_cards: list[int]            # card numbers still in circulation (not globally discarded)
    n_players: int                      # active player count
    player_card_counts: dict[int, int]  # player_id → exact card count (engine-verified)
    streak: int                         # consecutive plays without a doubt
    my_player_id: int
    prev_player_id: int
    next_player_id: int
    # — Raw event log — derive anything uncertain from here —
    history: list[GameEvent]


@dataclass
class TurnOutput:
    doubt: bool
    number: int | None  # declared number — only set on first hand
    cards: list[int] | None  # cards played — None when doubting


# ---------------------------------------------------------------------------
# History helpers — derive per-player statistics from the event log.
# Import these in bots instead of relying on pre-computed fields.
# ---------------------------------------------------------------------------

def honest_times(player_id: int, history: list[GameEvent]) -> int:
    """Times player was doubted and found to be honest (doubter was wrong)."""
    return sum(
        1 for e in history
        if isinstance(e, DoubtResolvedEvent) and e.target_id == player_id and not e.correct
    )


def dishonest_times(player_id: int, history: list[GameEvent]) -> int:
    """Times player was doubted and caught bluffing (doubter was correct)."""
    return sum(
        1 for e in history
        if isinstance(e, DoubtResolvedEvent) and e.target_id == player_id and e.correct
    )


def doubts_count(player_id: int, history: list[GameEvent]) -> int:
    """Number of times player chose to doubt."""
    return sum(
        1 for e in history
        if isinstance(e, DoubtResolvedEvent) and e.doubter_id == player_id
    )


def turns_count(player_id: int, history: list[GameEvent]) -> int:
    """Total turns taken by player (card plays + doubts)."""
    plays = sum(1 for e in history if isinstance(e, CardsPlayedEvent) and e.player_id == player_id)
    return plays + doubts_count(player_id, history)
