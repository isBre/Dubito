from .player import Player
from .game_data import TurnData, GameEvent


class TurnHandler:
    """Manages the turns of the game."""
    def __init__(self, all_players: list[Player]) -> None:
        self.counter = 0                        # incremental turn count
        self.position = len(all_players) - 1   # index into playing list
        self.streak = 0                         # consecutive plays without a doubt


class PlayersHandler:
    """Manages the players in the game."""
    def __init__(self, all_players: list[Player]) -> None:
        self.all = all_players
        self.playing = all_players.copy()
        self.winners = []
        self.prev = None
        self.this = None
        self.next = None
        self.empty_order: list[int] = []        # ids in hand-emptying order


class BoardHandler:
    """Manages the cards on the board."""
    def __init__(self, deck_size: int) -> None:
        self.cards = []
        self.number = 0                         # declared number (0 = first hand)
        self.availables = list(range(1, deck_size))
        self.latests = []                       # cards placed by the last player
        self.latest_author = None               # player id who placed latests


class GameHandler:
    """Manages the overall game state."""
    def __init__(self, all_players: list[Player], deck_size: int) -> None:
        self.turn = TurnHandler(all_players=all_players)
        self.players = PlayersHandler(all_players=all_players)
        self.board = BoardHandler(deck_size=deck_size)
        self.history: list[GameEvent] = []

    def append_event(self, event: GameEvent) -> None:
        self.history.append(event)

    def n_playing_players(self) -> int:
        return len(self.players.playing)

    def n_all_players(self) -> int:
        return len(self.players.all)

    def n_winners_players(self) -> int:
        return len(self.players.winners)

    def playing_players(self) -> list[Player]:
        return self.players.playing

    def playing_player(self, position: int) -> Player:
        return self.players.playing[position]

    def turn_position(self) -> int:
        return self.turn.position

    def increase_turn_counter(self) -> None:
        self.turn.counter += 1
        self.turn.streak += 1

    def next_turn(self) -> tuple[Player, Player]:
        self.increase_turn_counter()
        new_prev_player_pos = self.turn_position()
        new_this_player_pos = (new_prev_player_pos + 1) % self.n_playing_players()
        new_next_player_pos = (new_this_player_pos + 1) % self.n_playing_players()
        self.players.prev = self.playing_player(new_prev_player_pos)
        self.players.this = self.playing_player(new_this_player_pos)
        self.players.next = self.playing_player(new_next_player_pos)
        self.turn.position = new_this_player_pos
        return self.players.prev, self.players.this

    def is_first_hand(self) -> bool:
        return not self.board.cards

    def get_latest_played_cards(self) -> list[int]:
        return self.board.latests

    def get_current_number(self) -> int:
        return self.board.number

    def is_honest(self) -> bool:
        latest = self.get_latest_played_cards()
        current = self.get_current_number()
        return all(card == 0 or card == current for card in latest)

    def jokers_in_latest(self) -> list[int]:
        return [c for c in self.get_latest_played_cards() if c == 0]

    def get_board(self) -> list[int]:
        return self.board.cards

    def n_cards_board(self) -> int:
        return len(self.board.cards)

    def reset_board(self) -> None:
        self.board.cards = []
        self.board.number = 0
        self.turn.streak = 0
        self.board.latests = []
        self.board.latest_author = None

    def set_current_number(self, number: int) -> None:
        self.board.number = number

    def set_board_cards(self, cards: list[int], author_id: int | None = None) -> None:
        self.board.cards += cards
        self.board.latests = cards
        self.board.latest_author = author_id

    def has_open_claim(self, player: Player) -> bool:
        """True when `player` authored the play currently on top of the board.

        That play can still be doubted, so a hand-emptying play does not win
        until the next player's doubt window has passed."""
        return bool(self.board.latests) and self.board.latest_author == player.id

    def confirmable_winners(self) -> list[Player]:
        """Players whose win can be confirmed now: empty-handed with no open claim.

        Ordered by when each hand first became empty. Two players can become
        confirmable in the same turn (a deferred dump plus a doubter who eats
        the pile and discards down to zero); when only one confirmation slot
        remains before the game ends, the earliest dump must take it."""
        order = self.players.empty_order
        empty_now = {p.id for p in self.players.playing if p.has_no_cards()}
        order[:] = [pid for pid in order if pid in empty_now]
        for p in self.players.playing:
            if p.has_no_cards() and p.id not in order:
                order.append(p.id)
        by_id = {p.id: p for p in self.players.playing}
        return [by_id[pid] for pid in order if not self.has_open_claim(by_id[pid])]

    def set_discarded_cards(self, discarded: list[int]) -> None:
        self.board.availables = [x for x in self.board.availables if x not in discarded]

    def set_winners(self, winner: Player) -> None:
        self.players.winners.append(winner)
        self.players.playing.remove(winner)
        if not self.players.playing:
            return
        anchor = self.players.prev if winner is self.players.this else self.players.this
        if anchor in self.players.playing:
            self.turn.position = self.players.playing.index(anchor)
        else:
            self.turn.position = 0

    def get_winners(self) -> list[Player]:
        return self.players.winners


class StatsHandler:
    """Tracks per-player game statistics for post-game analytics (experiments, ML)."""
    def __init__(self, all_players: list[Player]) -> None:
        self.data = {}
        for p in all_players:
            self.data[p.id] = {
                'turns': 0,
                'not_first_turns': 0,
                'doubts': 0,
                'honest_times': 0,
                'dishonest_times': 0,
                'bluffs': 0,
                'successful_doubts': 0,
                'total_cards_played': 0,
                'play_turns': 0,
            }

    def increase_turns_played(self, player: Player, first_hand: bool) -> None:
        self.data[player.id]['turns'] += 1
        if not first_hand:
            self.data[player.id]['not_first_turns'] += 1

    def increase_player_doubts(self, player: Player) -> None:
        self.data[player.id]['doubts'] += 1

    def increase_player_honesty(self, player: Player) -> None:
        self.data[player.id]['honest_times'] += 1

    def increase_player_dishonesty(self, player: Player) -> None:
        self.data[player.id]['dishonest_times'] += 1

    def increase_player_bluffs(self, player: Player) -> None:
        self.data[player.id]['bluffs'] += 1

    def increase_player_successful_doubts(self, player: Player) -> None:
        self.data[player.id]['successful_doubts'] += 1

    def add_player_cards_played(self, player: Player, n: int) -> None:
        self.data[player.id]['total_cards_played'] += n
        self.data[player.id]['play_turns'] += 1


def generate_player_data(game_handler: GameHandler) -> TurnData:
    """Build the TurnData snapshot passed to player.play() each turn."""
    return TurnData(
        my_cards=list(game_handler.players.this.cards.hand),
        current_number=game_handler.get_current_number(),
        board_cards=game_handler.n_cards_board(),
        n_cards_played=len(game_handler.board.latests),
        playing_cards=list(game_handler.board.availables),
        n_players=game_handler.n_playing_players(),
        player_card_counts={p.id: len(p.cards) for p in game_handler.playing_players()},
        streak=game_handler.turn.streak,
        my_player_id=game_handler.players.this.id,
        prev_player_id=game_handler.players.prev.id,
        next_player_id=game_handler.players.next.id,
        history=list(game_handler.history),
    )
