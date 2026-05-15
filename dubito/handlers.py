from .player import Player
from .game_data import PlayerData, TurnData



class TurnHandler:
    """Manages the turns of the game."""
    def __init__(self, all_players: list[Player]) -> None:
        """
        Initialize a TurnHandler object.

        Parameters:
        - all_players (list[Player]): A list of all players participating in the game.
        """
        self.counter = 0  # Incremental value of game turns
        self.position = len(all_players) - 1  # Turn Position in [0, len(all_players)]
        self.streak = 0  # Number of turns without doubts

class PlayersHandler:
    """Manages the players in the game."""
    def __init__(self, all_players: list[Player]) -> None:
        """
        Initialize a PlayersHandler object.

        Parameters:
        - all_players (list[Player]): A list of all players participating in the game.
        """
        self.all = all_players  # All players (currently playing and not)
        self.playing = all_players.copy()  # Players that are playing 
        # (this is useful because if somebody wins it is removed from the game)
        self.winners = []  # Winning players list
        self.prev = None  # The Player that preceed this player
        self.this = None  # The Player we need to consider
        self.next = None  # The Player next to this player

class BoardHandler:
    """Manages the cards on the board."""
    def __init__(self, deck_size: int) -> None:
        """
        Initialize a BoardHandler object.

        Parameters:
        - deck_size (int): The size of the deck of cards.
        """
        self.cards = []  # Cards within the board
        self.number = 0  # the card number called from the previous player (0 means you're the first) 
        self.availables = list(range(1, deck_size))  # The number of cards that are not discarded yet
        self.latests = []  # Latest cards placed by the last player
        

class GameHandler:
    """Manages the overall game."""
    def __init__(
        self, 
        all_players: list[Player],
        deck_size: int,
    ) -> None:
        """
        Initialize a GameHandler object.

        Parameters:
        - all_players (list[Player]): A list of all players participating in the game.
        - deck_size (int): The size of the deck of cards.
        """
        self.turn = TurnHandler(all_players=all_players)
        self.players = PlayersHandler(all_players=all_players)
        self.board = BoardHandler(deck_size=deck_size)
        
    def n_playing_players(self) -> int:
        return len(self.players.playing)
    
    def n_all_players(self) -> int:
        return len(self.players.all)
    
    def n_winners_players(self) -> int:
        return len(self.players.winners)
    
    def playing_players(self) -> list[Player]:
        return self.players.playing
    
    def playing_player(self, position : int) -> Player:
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
    
    def get_current_number(self) -> list[int]:
        return self.board.number
    
    def is_honest(self) -> bool:
        latest = self.get_latest_played_cards()
        current = self.get_current_number()
        # Each card must either be a joker (wildcard) or match the declared number.
        # A joker only substitutes for its own slot — non-joker cards still need to match.
        return all(card == 0 or card == current for card in latest)

    def jokers_in_latest(self) -> list[int]:
        """Return list of joker cards (0) among the latest played cards."""
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
        
    def set_current_number(self, number : int) -> None:
        self.board.number = number
        
    def set_board_cards(self, cards : list[int]) -> None:
        self.board.cards += cards
        self.board.latests = cards
        
    def set_discarded_cards(self, discarded : list[int]) -> None:
        self.board.availables = [x for x in self.board.availables if x not in discarded]
        
    def set_winners(self, winner : Player) -> None:
        self.players.winners.append(winner)
        self.players.playing.remove(winner)
        # Edge Case, I update this_player position in case of winning
        self.turn.position = self.players.playing.index(self.players.this)
        
    def get_winners(self) -> list[Player]:
        return self.players.winners

 
class StatsHandler:
    """Manages statistical data of players."""
    def __init__(self, all_players: list[Player]) -> None:
        """
        Initialize a StatsHandler object.

        Parameters:
        - all_players (list[Player]): A list of all players participating in the game.
        """
        self.data = {}
        for p in all_players:
            self.data[p.id] = {
                'turns': 0,
                'not_first_turns': 0,
                'doubts': 0,
                'honest_times': 0,
                'dishonest_times': 0,
                'bluffs': 0,            # times player placed dishonest cards
                'successful_doubts': 0, # times player's doubt was correct
                'total_cards_played': 0,# total cards placed on board
                'play_turns': 0,        # turns where player placed cards (not doubted)
            }
            
    def increase_turns_played(self, player : Player, first_hand : bool) -> None:
        self.data[player.id]['turns'] += 1
        if not first_hand:
            self.data[player.id]['not_first_turns'] += 1
    
    def increase_player_doubts(self, player : Player) -> None:
        self.data[player.id]['doubts'] += 1
    
    def increase_player_honesty(self, player : Player) -> None:
        self.data[player.id]['honest_times'] += 1
    
    def increase_player_dishonesty(self, player : Player) -> None:
        self.data[player.id]['dishonest_times'] += 1

    def increase_player_bluffs(self, player: Player) -> None:
        self.data[player.id]['bluffs'] += 1

    def increase_player_successful_doubts(self, player: Player) -> None:
        self.data[player.id]['successful_doubts'] += 1

    def add_player_cards_played(self, player: Player, n: int) -> None:
        self.data[player.id]['total_cards_played'] += n
        self.data[player.id]['play_turns'] += 1


def generate_player_data(game_handler: GameHandler, stats_handler: StatsHandler) -> TurnData:
    """
    Generate player data based on the current game state.

    Parameters:
    - game_handler (GameHandler): The game handler object.
    - stats_handler (StatsHandler): The stats handler object.

    Returns:
    - TurnData: A dataclass containing the current turn state.
    """
    def _player_data(player: Player) -> PlayerData:
        s = stats_handler.data[player.id]
        return PlayerData(
            id=player.id,
            n_cards=len(player.cards),
            turns=s['turns'],
            not_first_turns=s['not_first_turns'],
            doubts=s['doubts'],
            honest_times=s['honest_times'],
            dishonest_times=s['dishonest_times'],
        )

    return TurnData(
        board_cards=game_handler.n_cards_board(),
        playing_cards=game_handler.board.availables,
        current_number=game_handler.get_current_number(),
        n_cards_played=len(game_handler.board.latests),
        streak=game_handler.turn.streak,
        n_players=game_handler.n_playing_players(),
        my_n_cards=len(game_handler.players.this.cards),
        me=_player_data(game_handler.players.this),
        prev=_player_data(game_handler.players.prev),
        next=_player_data(game_handler.players.next),
    )

