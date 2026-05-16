from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Game events — emitted to all players via observe() after each game action.
# Only observable information is included (card values are hidden until doubted).
# ---------------------------------------------------------------------------

@dataclass
class CardsPlayedEvent:
    player_id: int
    declared_number: int
    n_cards: int              # how many cards placed face-down


@dataclass
class DoubtResolvedEvent:
    doubter_id: int
    target_id: int            # the player who made the last play
    correct: bool             # True = bluffer caught; False = doubter wrong
    latest_cards: list[int]   # target's actual last play (now revealed)
    board_cards: list[int]    # cards the loser picks up (latest_cards minus jokers if any)
    declared_number: int
    jokers_discarded: int = 0

    @property
    def loser_id(self) -> int:
        return self.target_id if self.correct else self.doubter_id


@dataclass
class DiscardEvent:
    player_id: int
    card_number: int          # 4 of this number were removed from their hand


@dataclass
class PlayerWonEvent:
    player_id: int
    position: int             # 1 = first place, 2 = second, etc.


GameEvent = CardsPlayedEvent | DoubtResolvedEvent | DiscardEvent | PlayerWonEvent


# ---------------------------------------------------------------------------
# Turn data
# ---------------------------------------------------------------------------

@dataclass
class PlayerData:
    id: int
    n_cards: int
    turns: int
    not_first_turns: int
    doubts: int
    honest_times: int
    dishonest_times: int


@dataclass
class TurnData:
    board_cards: int
    playing_cards: list[int]
    current_number: int
    n_cards_played: int
    streak: int
    n_players: int
    my_n_cards: int
    me: PlayerData
    prev: PlayerData
    next: PlayerData


@dataclass
class TurnOutput:
    doubt: bool
    number: int | None  # declared number — only set on first hand
    cards: list[int] | None  # cards played — None when doubting
