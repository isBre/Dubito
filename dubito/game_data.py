from dataclasses import dataclass


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
