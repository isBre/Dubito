from typing import List, Tuple, Dict
import random
from pprint import pprint

from player import Player
from bots.rule_based import AlwaysTruthful, MrNoDoubt, MrDoubt, JustPutCards, RandomBoi
# from bots.probability import AdaptyBoi
from handlers import GameHandler, StatsHandler, generate_player_data, OutputPlayer
from machine_learning.dataset import DubitoDataset


def create_deck(deck_size: int = 14) -> List[int]:
    """
    Create a deck of cards.

    Args:
        deck_size (int, optional): The number of cards in the deck. Defaults to 14.

    Returns:
        List[int]: A shuffled list representing the deck of cards.
    """
    numbers = list(range(1, deck_size))
    deck = numbers * 4
    random.shuffle(deck)
    return deck

def assign_cards(deck: List[int], players: List[Player]):
    """
    Assigns cards from a deck to a list of players in a round-robin fashion.

    Parameters:
        deck (List[int]): A list of integers representing the cards to be distributed.
        players (List[Player]): A list of Player objects to whom the cards will be assigned.

    Returns:
        None
    """
    for i, card in enumerate(deck):
        players[i % len(players)].add_cards([card])

def has_n_equal_elements(card_counts: List[int], n: int):
    """
    Checks if any element in the list `card_counts` has a value greater than or equal to `n`.

    Args:
        card_counts (List[int]): A list of integers representing counts of elements.
        n (int): The value to compare each element against.

    Returns:
        bool: True if any element in `card_counts` has a value greater than or equal to `n`, False otherwise.
    """
    occurencies = list(card_counts.values())
    return any(occ >= n for occ in occurencies)

def initialize(all_players: List[Player], deck_size: int = 14) -> None:
    """
    Initializes the game by distributing cards to players and ensuring no player has four equal cards.

    Args:
        all_players (List[Player]): A list of Player objects representing all players in the game.
        deck_size (int, optional): The size of the deck to be used in the game. Defaults to 14.

    Returns:
        None
    """
    while True:
        # Reset players' cards before assigning new cards
        [player.reset() for player in all_players]
        # Distribute cards for each player's hand
        assign_cards(create_deck(deck_size), all_players)
        # Check if any player has 4 equal cards
        player_card_counts = [player.cards.count_all() for player in all_players]
        # If somebody has 4 equal cards, just restart this process from scratch, we dont want 4 equal cards
        if not any(has_n_equal_elements(count, 4) for count in player_card_counts):
            break



def dubito(
        all_players: List[Player],
        shuffle_players: bool = True,
        deck_size: int = 14,
        n_jollies: int = 2,  # TODO
) -> Tuple[Dict, Dict]:
    
    """
    Simulates a game of Dubito, a dynamic card game for 3-8 players. 
    Each player takes turns either making a play or doubting the previous player's move until only one player remains.

    Parameters:
        all_players (List[Player]): List of Player objects participating in the game.
        shuffle_players (bool, optional): Flag to shuffle player positions. Defaults to True.
        deck_size (int, optional): Size of the deck. Defaults to 14.
        n_jollies (int, optional): Number of jollies (not implemented). Defaults to 2.

    Returns:
        Tuple[Dict, Dict]: A tuple containing two dictionaries:
            - game_result: Contains information about the winners and losers of the game.
            - game_infos: Contains logs and decisions made during the game.
    """

    
    logger = ""
    
    # Shuffle players positions
    if shuffle_players: random.shuffle(all_players)
    # Deck and Player initialization
    initialize(all_players, deck_size)
    
    logger += f'\n{len(all_players)} Players are playing: {[f"Player{player.id}" for player in all_players]}'
    logger += f'\nGame Start!\n\n'
    
    game_handler = GameHandler(all_players = all_players, deck_size = deck_size)
    stats_handler = StatsHandler(all_players = all_players)
    dataset_handler = DubitoDataset()
    
    # If the player correctly doubt the previous player can play cards
    correct_doubt = False
    
    # Here i want to apply a semplification, game end only when one player win
    # In the actual game, the game ends when there are only two player left
    while game_handler.n_winners_players() < 1:
        
        # Just print all the cards of all playing players
        logger += f"\n\n------ Turn {game_handler.turn.counter} ------\n"
        logger += '\n'.join([f"Player{p.id}'s Cards: {p.cards}" for p in game_handler.playing_players()]) + '\n\n'
        
        # Get previous_player, this_player and next_player and update the turn values
        # If prev_player correctly doubted now he can place cards.
        if correct_doubt:
            correct_doubt = False
        else:
            prev_player, this_player = game_handler.next_turn()
        
        logger += f'Available Numbers: {game_handler.board.availables}\n'
        logger += f'Is Player{this_player.id}\'s turn! ({this_player.__class__.__name__})\n'
        logger += f'Player{this_player.id} ({this_player.__class__.__name__}) has: {this_player.cards}\n'

        # Player Move
        input_player = generate_player_data(game_handler = game_handler, stats_handler = stats_handler)
        untouched_hand = this_player.cards.hand.copy()
        dict_output_player = this_player.play(input_player)
        dataset_handler.add_data(untouched_hand, this_player.id, input_player, dict_output_player)
        output_player = OutputPlayer(dict_output_player)
        stats_handler.increase_turns_played(this_player, game_handler.is_first_hand())

        # Handle Exeptions
        if output_player.is_doubting() and game_handler.is_first_hand():
            raise Exception(f"Player{this_player.id} cannot doubt in the first round")

        # This_Player is doubting
        elif output_player.is_doubting():
            stats_handler.increase_player_doubts(this_player)
            logger += f'Player{this_player.id} ({this_player.__class__.__name__}) doubt Player{prev_player.id} ({prev_player.__class__.__name__})!\n'
            # Check if the last card(s) played from the last player are correct
            # a.k.a. Prev_Player is bluffing or not
            if game_handler.is_honest():
                # This_Player get all the cards
                this_player.add_cards(game_handler.get_board())
                # Update player knowledge about other players
                stats_handler.increase_player_honesty(prev_player)
                logger += f"Player{this_player.id} ({this_player.__class__.__name__}) get all ({game_handler.n_cards_board()}) the cards!\n"
            else:
                correct_doubt = True
                # Prev_Player get all the cards
                prev_player.add_cards(game_handler.get_board())
                # Update player knowledge about other players
                stats_handler.increase_player_dishonesty(prev_player)
                logger += f"Player{prev_player.id} ({prev_player.__class__.__name__}) get all ({game_handler.n_cards_board()}) the cards!\n"
            game_handler.reset_board()

        # If This_Player play cards
        else:
            # If number_playing was zero means that this is the first hand
            if game_handler.is_first_hand():
                # So the first number should be chosed by this_player
                new_value = output_player.get_number()
                game_handler.set_current_number(new_value)
                logger += f"Player{this_player.id} call number {new_value}\n"
            # Update the board
            new_cards = output_player.get_cards()
            game_handler.set_board_cards(new_cards)
            logger += f"Player{this_player.id} play {new_cards}\n"

        # Discard phase
        for p in game_handler.playing_players():
            discarded_cards = p.discard_cards()
            if discarded_cards: logger += f"Player{p.id} removed: {discarded_cards}\n"
            game_handler.set_discarded_cards(discarded_cards)

        # Won phase
        if prev_player.has_no_cards():
            logger += f"Player{prev_player.id} Won!\n"
            game_handler.set_winners(prev_player)
            logger += f"{game_handler.n_playing_players()} Players remaining!\n"

    logger += f"\n------ End Game ------"
    logger += f"\nWinners: {[f'Player{p.id}' for p in game_handler.get_winners()]}\n"
    logger += f"Losers: {[f'Player{p.id}' for p in game_handler.playing_players()]}"
    
    dataset_handler.add_result(game_handler.get_winners(), game_handler.playing_players())
    
    game_result = {'winners' : game_handler.get_winners(), 'losers' : game_handler.playing_players()}
    game_infos = {'logs' : logger, 'decisions' : dataset_handler.get_dataset(), 'stats' : stats_handler}

    return game_result, game_infos


if __name__ == "__main__":
    value = dubito(
        all_players = [AlwaysTruthful(1), MrNoDoubt(2), JustPutCards(3), RandomBoi(4), MrDoubt(5)],
        shuffle_players = False,
    )
    results, infos = value
    print(infos['decisions'])
