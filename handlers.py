from player import Player

from typing import List, Tuple, Dict


class TurnHandler:
    def __init__(self, all_players : List[Player]) -> None:
        self.counter = 0 # Incremental value of game turns
        self.position = len(all_players) - 1 # Turn Position in [0, len(all_players)]
        self.streak = 0 # Number of turns without doubts

class PlayersHandler:
    def __init__(self, all_players : List[Player]) -> None:
        self.all = all_players # All players (currently playing and not)
        self.playing = all_players.copy() # Players that are playing 
        # (this is useful because if somebody wins it is removed from the game)
        self.winners = [] # Winning players list
        self.prev = None # The Player that preceed this player
        self.this = None # The Player we need to consider
        self.next = None # The Player next to this player

class BoardHandler:
    def __init__(self, deck_size : int) -> None:
        self.cards = [] # Cards within the board
        self.number = 0 # the card number called from the previous player (0 means you're the first) 
        self.availables = list(range(1, deck_size)) # The number of cards that are not discarded yet
        self.latests = [] # Latest cards placed by the last player
        

class GameHandler:
    def __init__(
        self, 
        all_players: List[Player],
        deck_size : int,
    ) -> None:
        self.turn = TurnHandler(all_players = all_players)
        self.players = PlayersHandler(all_players = all_players)
        self.board = BoardHandler(deck_size = deck_size)
        
    def n_playing_players(self) -> int:
        return len(self.players.playing)
    
    def n_all_players(self) -> int:
        return len(self.players.all)
    
    def n_winners_players(self) -> int:
        return len(self.players.winners)
    
    def playing_players(self) -> List[Player]:
        return self.players.playing
    
    def playing_player(self, position : int) -> Player:
        return self.players.playing[position]
    
    def turn_position(self) -> int:
        return self.turn.position
    
    def increase_turn_counter(self) -> None:
        self.turn.counter += 1
        self.turn.streak += 1
    
    def next_turn(self) -> Tuple[Player, Player]:
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
    
    def get_latest_played_cards(self) -> List[int]:
        return self.board.latests
    
    def get_current_number(self) -> list[int]:
        return self.board.number
    
    def is_honest(self) -> bool:
        return all(card == self.get_current_number() for card in self.get_latest_played_cards())
    
    def get_board(self) -> List[int]:
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
        
    def set_board_cards(self, cards : List[int]) -> None:
        self.board.cards += cards
        self.board.latests = cards
        
    def set_discarded_cards(self, discarded : List[int]) -> None:
        self.board.availables = [x for x in self.board.availables if x not in discarded]
        
    def set_winners(self, winner : Player) -> None:
        self.players.winners.append(winner)
        self.players.playing.remove(winner)
        # Edge Case, I update this_player position in case of winning
        self.turn.position = self.players.playing.index(self.players.this)
        
    def get_winners(self) -> List[Player]:
        return self.players.winners

 
class StatsHandler:
    # Keep track of mayor stats in order to make more precise decisions
    
    def __init__(self, 
            all_players: List[Player],
    ) -> None:
        self.data = {}
        for p in all_players:
            self.data[p.id] = {
                'turns' : 0, # How many turns the player played
                'not_first_turns' : 0, # How many turns the player played (not first hand)
                'doubts' : 0, # Number of times the player doubted
                'honest_times' : 0, # Number of times recorded that this player was honest when doubted
                'dishonest_times' : 0, # number of times recorded that this player was dishonest when doubted
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


def generate_player_data(game_handler : GameHandler, stats_handler : StatsHandler) -> Dict:
    data = {
        # Number of cards in the board (0 means you're the first)
        'board_cards': game_handler.n_cards_board(),
        # All numbers without discarded cards
        'playing_cards' : game_handler.board.availables,
        # the card number called from the previous player (0 means you're the first)
        'current_number': game_handler.get_current_number(),
        # Number of cards played by the previous player
        'n_cards_played' : len(game_handler.board.latests),
        # Number of turns without doubts
        'streak' : game_handler.turn.streak,
    }
    prev_player = game_handler.players.prev
    next_player = game_handler.players.next
    data['prev'] = stats_handler.data[prev_player.id]
    data['prev']['id'] = prev_player.id
    data['prev']['n_cards'] = len(prev_player.cards)
    data['next'] = stats_handler.data[next_player.id]
    data['next']['id'] = next_player.id
    data['next']['n_cards'] = len(next_player.cards)
        
    return data

class OutputPlayer:
    
    def __init__(self, output : Dict) -> None:
        self.output = output
        # TODO assert
    
    def is_doubting(self) -> bool:
        return self.output['doubt']
    
    def get_number(self) -> bool:
        return self.output['number']
    
    def get_cards(self) -> List[int]:
        return self.output['cards']