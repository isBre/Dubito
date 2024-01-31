from typing import List, Tuple, Dict
import random
from collections import Counter

import yaml

import players_algorithm


def create_deck(deck_size : int = 14) -> List[int]:
    # Generate numbers from 1 to 13
    numbers = list(range(1, deck_size))
    # Repeat each number 4 times
    deck = numbers * 4
    # Shuffle the deck
    random.shuffle(deck)
    return deck


def assign_cards(deck : List[int], players : List[players_algorithm.Player]):
    # Distribute cards in a round-robin fashion
    for i, card in enumerate(deck):
        players[i % len(players)].add_cards([card])


def has_n_equal_elements(card_counts : List[int], n : int):
    return any(count >= n for count in card_counts.values())


def initialize(all_players : List[players_algorithm.Player], deck_size : int = 14):
    while True:
        # Reset players' cards before assigning new cards
        for player in all_players:
            player.reset()
        assign_cards(create_deck(deck_size), all_players)
        # Check if any player has 4 equal cards
        player_card_counts = [player.cards.count_all() for player in all_players]
        if not any(has_n_equal_elements(count, 4) for count in player_card_counts):
            break

def next_turn_positions(global_infos : Dict) -> Tuple[int, int, int]:
    n_players = len(global_infos['players']['playing'])
    this_player_pos = global_infos['turn_pos']
    new_previous_player_pos = this_player_pos
    new_this_player_pos = (this_player_pos + 1) % n_players
    new_next_player_pos = (new_this_player_pos + 1) % n_players
    return new_previous_player_pos, new_this_player_pos, new_next_player_pos


def next_turn_players(
        global_infos : Dict,
        player_positions : Tuple[int, int, int]
) -> Tuple[players_algorithm.Player, players_algorithm.Player, players_algorithm.Player]:
    previous_player_pos, this_player_pos, next_player_pos = player_positions
    global_infos['players']['prev'] = global_infos['players']['playing'][previous_player_pos]
    global_infos['players']['this'] = global_infos['players']['playing'][this_player_pos]
    global_infos['players']['next'] = global_infos['players']['playing'][next_player_pos]
    return global_infos['players']['prev'], global_infos['players']['this'], global_infos['players']['next']


def game(
        all_players : List[players_algorithm.Player],
        shuffle_players: bool = True,
        deck_size : int = 14,
        n_number_repetitions : int  = 4, #TODO
        n_aces : int = 2, #TODO
        verbose : int = 0,
) -> Tuple[List[players_algorithm.Player], List[players_algorithm.Player], List[players_algorithm.Player]]:
    
    if shuffle_players: random.shuffle(all_players)
    # Give turn position in this game
    for idx, player in enumerate(all_players):
        player.initial_infos(game_position = idx + 1)
    if verbose: print(f'{len(all_players)} Players are playing: {[f"Player{player.id}" for player in all_players]}')
    initialize(all_players, deck_size)
    if verbose: print(f'Game Start!')

    # Variables
    global_infos = {
        'turn_pos' : len(all_players) - 1,
        'players' : {
            "playing" : all_players.copy(),
            "previous" : None,
            "this" : None,
            "next" : None},
        'board' : [],
        'winners' : []
    }
    turn_infos = {
        'board' : {
            'n_cards' : 0 # Number of cards in the board (0 means you're the first)
            }, 
        'current_number' : 0, # the card number called from the previous player (0 means you're the first)
        'prev' : { # infos about previous player
            'name' : "", # name (id) of the previous player
            'n_cards' : 0, #numbers of cards in the previous_player hand
            'n_cards_placed' : 0, #numbers of cards played by the previous player (0 means you're the first)
            },
        'next' : { # infos about previous player
            'name' : "", # name (id) of the previous player
            'n_cards' : 0, #numbers of cards in the next_player hand
            }
    }

    # Game end when there are only 2 players
    while len(global_infos['players']['playing']) > 2:
        
        #Just print all the cards of all players
        if verbose == 2:
            for p in global_infos['players']['playing']:
                print(f"Player{p.id}'s Cards: {p.cards}")
        
        # This is an assertion to verify that all parameters are updated correctly
        assert ((turn_infos['board']['n_cards'] == turn_infos['current_number'] == turn_infos['prev']['n_cards_placed'] == len(global_infos['board']) == 0) or
                (turn_infos['board']['n_cards'] != 0 and turn_infos['current_number'] != 0 and turn_infos['prev']['n_cards_placed'] != 0 and len(global_infos['board']) != 0))
        
        # Get previous_player, this_player and next_player and update the turn values
        positions = next_turn_positions(global_infos)
        _, this_player_pos, _ = positions
        previous_player, this_player, next_player = next_turn_players(global_infos, positions)
        global_infos['turn_pos'] = this_player_pos
        if verbose: print(f'Is Player{this_player.id}\'s turn! ({this_player.__class__.__name__})')
        if verbose: print(f'Player{this_player.id} has: {this_player.cards}')

        # Player play
        turn_infos['prev']['name'] = previous_player.id,
        turn_infos['prev']['n_cards'] = previous_player.n_cards()
        turn_infos['next']['name'] = next_player.id,
        turn_infos['next']['n_cards'] = next_player.n_cards()
        player_move = this_player.play(turn_infos)
        
        if 'doubt' in player_move and not(turn_infos['current_number']):
            raise Exception(f"Player{this_player.id} cannot doubt in the first round")
        
        # If this_player doubt
        elif 'doubt' in player_move:
            if verbose: print(f'Player{this_player.id} doubt Player{previous_player.id}!')
            # Check if the last card(s) played from the last player are correct
            if all(card == turn_infos['current_number'] for card in global_infos['board'][- turn_infos['prev']['n_cards_placed']:]):
                # this_player get all the cards
                this_player.add_cards(global_infos['board'])
                # Possibly update player knowledge about other players
                for p in global_infos['players']['playing']:
                    p.update(previous_player, True)
                if verbose: print(f"Player{this_player.id} get all ({len(global_infos['board'])}) the cards!")
            else:
                # previous_player get all the cards
                previous_player.add_cards(global_infos['board'])
                # Possibly update player knowledge about other players
                for p in global_infos['players']['playing']:
                    p.update(previous_player, False)
                if verbose: print(f"Player{previous_player.id} get all ({len(global_infos['board'])}) the cards!")
            global_infos['board'] = []
            turn_infos['board']['n_cards'] = 0
            turn_infos['current_number'] = 0
            turn_infos['prev']['n_cards_placed'] = 0
        
        # If this_player play cards
        elif 'card_played' in player_move:
            if 'current_number' in player_move and not(turn_infos['current_number']):
                # If number_playing was zero means that this is the first hand, so the first number
                # should be chosed by this_player
                turn_infos['current_number'] = player_move['current_number']
                if verbose: print(f"Player{this_player.id} call number {player_move['current_number']}")
            # Update the board
            global_infos['board'] += player_move['card_played']
            turn_infos['board']['n_cards'] = len(global_infos['board'])
            turn_infos['prev']['n_cards_placed'] = len(player_move['card_played'])
            if verbose: print(f"Player{this_player.id} play {player_move['card_played']}")
        
        # Discard phase
        for p in global_infos['players']['playing']:
            discarded_cards = p.discard_cards() 
            if discarded_cards:
                if verbose: print(f"Player{p.id} removed: {discarded_cards}")
        
        # Won phase
        if previous_player.has_no_cards():
            if verbose: print(f"Player{previous_player.id} Won!")
            global_infos['players']['playing'].remove(previous_player)
            global_infos['winners'].append(previous_player)
            if verbose: print(f"{len(global_infos['players']['playing'])} Players remaining!")
            # Edge Case, I update this_player position in case of winning
            global_infos['turn_pos'] = global_infos['players']['playing'].index(this_player)

        if verbose == 2: input("Press Enter to continue...")
    
    if verbose: print(f"Winners: {[f'Player{p.id}' for p in global_infos['winners']]}")
    if verbose: print(f"Losers: {[f'Player{p.id}' for p in global_infos['players']['playing']]}")
    
    return global_infos['winners'], global_infos['players']['playing']


if __name__ == "__main__":
    game(verbose = 1)