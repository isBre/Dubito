import random
from collections import Counter
from pprint import pprint

from .player import Player
from bots.manual.rule_based import AlwaysTruthful, MrNoDoubt, MrDoubt, JustPutCards, RandomBoi
# from bots.manual.probability import AdaptyBoi
from .handlers import GameHandler, StatsHandler, generate_player_data
from .game_data import CardsPlayedEvent, DoubtResolvedEvent, DiscardEvent, PlayerWonEvent
from machine_learning.dataset import DubitoDataset


def _emit(players: list[Player], event) -> None:
    for p in players:
        p.observe(event)


def create_deck(deck_size: int = 14, n_jollies: int = 0) -> list[int]:
    """
    Create a deck of cards.

    Args:
        deck_size (int, optional): The number of cards in the deck. Defaults to 14.
        n_jollies (int, optional): Number of joker cards to add. Defaults to 0.

    Returns:
        list[int]: A shuffled list representing the deck of cards.
    """
    numbers = list(range(1, deck_size))
    deck = numbers * 4 + [0] * n_jollies
    random.shuffle(deck)
    return deck

def assign_cards(deck: list[int], players: list[Player]):
    """
    Assigns cards from a deck to a list of players in a round-robin fashion.

    Parameters:
        deck (list[int]): A list of integers representing the cards to be distributed.
        players (list[Player]): A list of Player objects to whom the cards will be assigned.

    Returns:
        None
    """
    for i, card in enumerate(deck):
        players[i % len(players)].add_cards([card])

def has_n_equal_elements(card_counts: Counter, n: int) -> bool:
    """
    Checks if any card in the counter has a count greater than or equal to `n`.

    Args:
        card_counts (Counter): A Counter mapping card values to their counts.
        n (int): The minimum count to check against.

    Returns:
        bool: True if any card appears at least `n` times, False otherwise.
    """
    occurencies = list(card_counts.values())
    return any(occ >= n for occ in occurencies)

def initialize(all_players: list[Player], deck_size: int = 14, n_jollies: int = 0) -> None:
    """
    Initializes the game by distributing cards to players and ensuring no player has four equal cards.

    Args:
        all_players (list[Player]): A list of Player objects representing all players in the game.
        deck_size (int, optional): The size of the deck to be used in the game. Defaults to 14.
        n_jollies (int, optional): Number of joker cards to include. Defaults to 0.

    Returns:
        None
    """
    while True:
        # Reset players' cards before assigning new cards
        [player.reset() for player in all_players]
        # Distribute cards for each player's hand
        assign_cards(create_deck(deck_size, n_jollies), all_players)
        # Check if any player has 4 equal cards
        player_card_counts = [player.cards.count_all() for player in all_players]
        # If somebody has 4 equal cards, just restart this process from scratch, we dont want 4 equal cards
        if not any(has_n_equal_elements(count, 4) for count in player_card_counts):
            break



def dubito(
        all_players: list[Player],
        shuffle_players: bool = True,
        deck_size: int = 14,
        n_jollies: int = 2,  # TODO
        max_turns: int = 1_000,
) -> tuple[dict, dict]:
    
    """
    Simulates a game of Dubito, a dynamic card game for 3-8 players. 
    Each player takes turns either making a play or doubting the previous player's move until only one player remains.

    Parameters:
        all_players (list[Player]): List of Player objects participating in the game.
        shuffle_players (bool): Flag to shuffle player positions. Defaults to True.
        deck_size (int): Size of the deck. Defaults to 14.
        n_jollies (int): Number of joker cards added to the deck. Defaults to 2.
        max_turns (int): Safety cap on the number of turns. Defaults to 1_000.
            If reached, all remaining players are treated as losers.

    Returns:
        tuple[dict, dict]: A tuple containing two dictionaries:
            - game_result: Contains information about the winners and losers of the game.
            - game_infos: Contains logs and decisions made during the game.
    """

    
    logger = ""
    
    # Shuffle players positions
    if shuffle_players: random.shuffle(all_players)
    # Deck and Player initialization
    initialize(all_players, deck_size, n_jollies)
    
    logger += f'\n{len(all_players)} Players are playing: {[f"Player{player.id}" for player in all_players]}'
    logger += f'\nGame Start!\n\n'
    
    game_handler = GameHandler(all_players = all_players, deck_size = deck_size)
    stats_handler = StatsHandler(all_players = all_players)
    dataset_handler = DubitoDataset()
    
    # When True: doubter caught the bluffer, so the doubter replays without advancing turns.
    replay_turn = False
    
    while game_handler.n_playing_players() > 2 and game_handler.turn.counter < max_turns:
        
        # Just print all the cards of all playing players
        logger += f"\n\n------ Turn {game_handler.turn.counter} ------\n"
        logger += '\n'.join([f"Player{p.id}'s Cards: {p.cards}" for p in game_handler.playing_players()]) + '\n\n'
        
        # Get previous_player, this_player and next_player and update the turn values
        # If prev_player correctly doubted now he can place cards.
        if replay_turn:
            replay_turn = False
        else:
            prev_player, this_player = game_handler.next_turn()
        
        logger += f'Available Numbers: {game_handler.board.availables}\n'
        logger += f'Is Player{this_player.id}\'s turn! ({this_player.__class__.__name__})\n'
        logger += f'Player{this_player.id} ({this_player.__class__.__name__}) has: {this_player.cards}\n'

        # Player Move
        input_player = generate_player_data(game_handler = game_handler, stats_handler = stats_handler)
        untouched_hand = this_player.cards.hand.copy()
        output = this_player.play(input_player)
        dataset_handler.add_data(untouched_hand, this_player.id, input_player, output)
        stats_handler.increase_turns_played(this_player, game_handler.is_first_hand())

        # Handle Exceptions
        if output.doubt and game_handler.is_first_hand():
            raise Exception(f"Player{this_player.id} cannot doubt in the first round")

        # This_Player is doubting
        elif output.doubt:
            stats_handler.increase_player_doubts(this_player)
            logger += f'Player{this_player.id} ({this_player.__class__.__name__}) doubt Player{prev_player.id} ({prev_player.__class__.__name__})!\n'

            # Snapshot board before any mutation — used for the event below
            latest_cards_snap = list(game_handler.get_latest_played_cards())
            full_board_snap = list(game_handler.get_board())
            declared_snap = game_handler.get_current_number()

            jokers_played = game_handler.jokers_in_latest()
            if game_handler.is_honest() and jokers_played:
                # Joker protection: play was honest (joker ± matching cards).
                # Jokers are discarded; remaining board cards go to the doubter.
                board_cards = list(game_handler.get_board())
                for j in jokers_played:
                    board_cards.remove(j)
                this_player.add_cards(board_cards)
                stats_handler.increase_player_honesty(prev_player)
                logger += f"Joker revealed! Player{this_player.id} ({this_player.__class__.__name__}) gets {len(board_cards)} cards, {len(jokers_played)} joker(s) discarded!\n"
                doubt_event = DoubtResolvedEvent(
                    doubter_id=this_player.id, target_id=prev_player.id, correct=False,
                    latest_cards=latest_cards_snap, board_cards=board_cards,
                    declared_number=declared_snap, jokers_discarded=len(jokers_played),
                )
            elif game_handler.is_honest():
                # This_Player get all the cards
                this_player.add_cards(game_handler.get_board())
                stats_handler.increase_player_honesty(prev_player)
                logger += f"Player{this_player.id} ({this_player.__class__.__name__}) get all ({game_handler.n_cards_board()}) the cards!\n"
                doubt_event = DoubtResolvedEvent(
                    doubter_id=this_player.id, target_id=prev_player.id, correct=False,
                    latest_cards=latest_cards_snap, board_cards=full_board_snap,
                    declared_number=declared_snap,
                )
            else:
                replay_turn = True
                # Prev_Player get all the cards (any jokers already in the board are kept by prev_player)
                prev_player.add_cards(game_handler.get_board())
                stats_handler.increase_player_dishonesty(prev_player)
                stats_handler.increase_player_successful_doubts(this_player)
                logger += f"Player{prev_player.id} ({prev_player.__class__.__name__}) get all ({game_handler.n_cards_board()}) the cards!\n"
                doubt_event = DoubtResolvedEvent(
                    doubter_id=this_player.id, target_id=prev_player.id, correct=True,
                    latest_cards=latest_cards_snap, board_cards=full_board_snap,
                    declared_number=declared_snap,
                )
            game_handler.reset_board()
            _emit(game_handler.playing_players(), doubt_event)

        # If This_Player play cards
        else:
            # If number_playing was zero means that this is the first hand
            if game_handler.is_first_hand():
                # So the first number should be chosen by this_player
                new_value = output.number
                # A joker (0) cannot be the declared number; fall back to a random valid number
                if new_value == 0:
                    pool = game_handler.board.availables or output.cards
                    new_value = random.choice(pool)
                game_handler.set_current_number(new_value)
                logger += f"Player{this_player.id} call number {new_value}\n"
            # Update the board
            new_cards = output.cards
            game_handler.set_board_cards(new_cards)
            stats_handler.add_player_cards_played(this_player, len(new_cards))
            if not game_handler.is_honest():
                stats_handler.increase_player_bluffs(this_player)
            logger += f"Player{this_player.id} play {new_cards}\n"
            _emit(game_handler.playing_players(), CardsPlayedEvent(
                player_id=this_player.id,
                declared_number=game_handler.get_current_number(),
                n_cards=len(new_cards),
            ))

        # Discard phase
        for p in game_handler.playing_players():
            discarded_cards = p.discard_cards()
            if discarded_cards:
                logger += f"Player{p.id} removed: {discarded_cards}\n"
                # discarded_cards is a list of unique card values that were removed
                _emit(game_handler.playing_players(), DiscardEvent(
                    player_id=p.id,
                    card_number=discarded_cards[0],
                ))
            game_handler.set_discarded_cards(discarded_cards)

        # Won phase — check every playing player; any player can reach 0 cards via the
        # discard phase, not just prev_player.  Snapshot the list before iterating so
        # set_winners() mutations don't affect the loop.
        for winner in [p for p in game_handler.playing_players() if p.has_no_cards()]:
            logger += f"Player{winner.id} Won!\n"
            game_handler.set_winners(winner)
            logger += f"{game_handler.n_playing_players()} Players remaining!\n"
            _emit(game_handler.playing_players(), PlayerWonEvent(
                player_id=winner.id,
                position=len(game_handler.get_winners()),
            ))

    logger += f"\n------ End Game ------"
    if game_handler.turn.counter >= max_turns:
        logger += f"\nTurn limit ({max_turns}) reached — all remaining players count as losers."
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
