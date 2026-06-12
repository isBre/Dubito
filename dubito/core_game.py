import random
from collections import Counter

from .player import Player
from .handlers import GameHandler, StatsHandler, generate_player_data
from .game_data import CardsPlayedEvent, DoubtResolvedEvent, DiscardEvent, PlayerWonEvent, GameStartEvent
from machine_learning.dataset import DubitoDataset



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
        [player.reset() for player in all_players]
        assign_cards(create_deck(deck_size, n_jollies), all_players)
        player_card_counts = [player.cards.count_all() for player in all_players]
        if not any(has_n_equal_elements(count, 4) for count in player_card_counts):
            break



def _resolve_doubt(
        game_handler: GameHandler,
        this_player: Player,
        prev_player: Player,
        stats_handler: StatsHandler,
) -> tuple[bool, str]:
    """Resolves a doubt action. Returns (replay_turn, log_snippet)."""
    log = f'Player{this_player.id} ({this_player.__class__.__name__}) doubt Player{prev_player.id} ({prev_player.__class__.__name__})!\n'
    stats_handler.increase_player_doubts(this_player)

    latest_cards_snap = list(game_handler.get_latest_played_cards())
    full_board_snap = list(game_handler.get_board())
    declared_snap = game_handler.get_current_number()
    jokers_played = game_handler.jokers_in_latest()

    if game_handler.is_honest() and jokers_played:
        board_cards = list(game_handler.get_board())
        for j in jokers_played:
            board_cards.remove(j)
        this_player.add_cards(board_cards)
        stats_handler.increase_player_honesty(prev_player)
        log += f"Joker revealed! Player{this_player.id} ({this_player.__class__.__name__}) gets {len(board_cards)} cards, {len(jokers_played)} joker(s) discarded!\n"
        event = DoubtResolvedEvent(
            doubter_id=this_player.id, target_id=prev_player.id, correct=False,
            latest_cards=latest_cards_snap, board_cards=board_cards,
            declared_number=declared_snap, jokers_discarded=len(jokers_played),
        )
        replay = False

    elif game_handler.is_honest():
        this_player.add_cards(game_handler.get_board())
        stats_handler.increase_player_honesty(prev_player)
        log += f"Player{this_player.id} ({this_player.__class__.__name__}) get all ({game_handler.n_cards_board()}) the cards!\n"
        event = DoubtResolvedEvent(
            doubter_id=this_player.id, target_id=prev_player.id, correct=False,
            latest_cards=latest_cards_snap, board_cards=full_board_snap,
            declared_number=declared_snap,
        )
        replay = False

    else:
        prev_player.add_cards(game_handler.get_board())
        stats_handler.increase_player_dishonesty(prev_player)
        stats_handler.increase_player_successful_doubts(this_player)
        log += f"Player{prev_player.id} ({prev_player.__class__.__name__}) get all ({game_handler.n_cards_board()}) the cards!\n"
        event = DoubtResolvedEvent(
            doubter_id=this_player.id, target_id=prev_player.id, correct=True,
            latest_cards=latest_cards_snap, board_cards=full_board_snap,
            declared_number=declared_snap,
        )
        replay = True

    game_handler.reset_board()
    game_handler.append_event(event)
    return replay, log


def _handle_play(
        game_handler: GameHandler,
        this_player: Player,
        output,
        stats_handler: StatsHandler,
) -> str:
    """Handles a card-play action. Returns a log snippet."""
    log = ""
    if game_handler.is_first_hand():
        new_value = output.number
        if new_value == 0:
            pool = game_handler.board.availables or output.cards
            new_value = random.choice(pool)
        game_handler.set_current_number(new_value)
        log += f"Player{this_player.id} call number {new_value}\n"

    new_cards = output.cards
    game_handler.set_board_cards(new_cards)
    stats_handler.add_player_cards_played(this_player, len(new_cards))
    if not game_handler.is_honest():
        stats_handler.increase_player_bluffs(this_player)
    log += f"Player{this_player.id} play {new_cards}\n"
    game_handler.append_event(CardsPlayedEvent(
        player_id=this_player.id,
        declared_number=game_handler.get_current_number(),
        n_cards=len(new_cards),
    ))
    return log


def _process_end_of_turn(game_handler: GameHandler) -> str:
    """Runs discards and winner detection. Returns a log snippet."""
    log = ""
    for p in game_handler.playing_players():
        discarded_cards = p.discard_cards()
        if discarded_cards:
            log += f"Player{p.id} removed: {discarded_cards}\n"
            for card_number in discarded_cards:
                game_handler.append_event(DiscardEvent(
                    player_id=p.id,
                    card_number=card_number,
                ))
        game_handler.set_discarded_cards(discarded_cards)

    for winner in [p for p in game_handler.playing_players() if p.has_no_cards()]:
        log += f"Player{winner.id} Won!\n"
        game_handler.set_winners(winner)
        log += f"{game_handler.n_playing_players()} Players remaining!\n"
        game_handler.append_event(PlayerWonEvent(
            player_id=winner.id,
            position=len(game_handler.get_winners()),
        ))
    return log


def dubito(
        all_players: list[Player],
        shuffle_players: bool = True,
        deck_size: int = 14,
        n_jollies: int = 2,
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

    if shuffle_players:
        random.shuffle(all_players)
    initialize(all_players, deck_size, n_jollies)

    logger += f'\n{len(all_players)} Players are playing: {[f"Player{player.id}" for player in all_players]}'
    logger += f'\nGame Start!\n\n'

    game_handler = GameHandler(all_players=all_players, deck_size=deck_size)
    stats_handler = StatsHandler(all_players=all_players)
    dataset_handler = DubitoDataset()

    game_handler.append_event(GameStartEvent(
        player_ids=[p.id for p in all_players],
        initial_card_counts={p.id: len(p.cards) for p in all_players},
    ))

    replay_turn = False

    while game_handler.n_playing_players() > 2 and game_handler.turn.counter < max_turns:

        logger += f"\n\n------ Turn {game_handler.turn.counter} ------\n"
        logger += '\n'.join([f"Player{p.id}'s Cards: {p.cards}" for p in game_handler.playing_players()]) + '\n\n'

        if replay_turn:
            replay_turn = False
        else:
            prev_player, this_player = game_handler.next_turn()

        logger += f'Available Numbers: {game_handler.board.availables}\n'
        logger += f'Is Player{this_player.id}\'s turn! ({this_player.__class__.__name__})\n'
        logger += f'Player{this_player.id} ({this_player.__class__.__name__}) has: {this_player.cards}\n'

        input_player = generate_player_data(game_handler)
        untouched_hand = this_player.cards.hand.copy()
        output = this_player.play(input_player)
        dataset_handler.add_data(untouched_hand, this_player.id, input_player, output)
        stats_handler.increase_turns_played(this_player, game_handler.is_first_hand())

        if output.doubt and game_handler.is_first_hand():
            raise Exception(f"Player{this_player.id} cannot doubt in the first round")
        elif output.doubt:
            replay_turn, doubt_log = _resolve_doubt(game_handler, this_player, prev_player, stats_handler)
            logger += doubt_log
        else:
            logger += _handle_play(game_handler, this_player, output, stats_handler)

        logger += _process_end_of_turn(game_handler)

    logger += f"\n------ End Game ------"
    if game_handler.turn.counter >= max_turns:
        logger += f"\nTurn limit ({max_turns}) reached — all remaining players count as losers."
    logger += f"\nWinners: {[f'Player{p.id}' for p in game_handler.get_winners()]}\n"
    logger += f"Losers: {[f'Player{p.id}' for p in game_handler.playing_players()]}"

    dataset_handler.add_result(game_handler.get_winners(), game_handler.playing_players())

    game_result = {'winners': game_handler.get_winners(), 'losers': game_handler.playing_players()}
    game_infos = {'logs': logger, 'decisions': dataset_handler.get_dataset(), 'stats': stats_handler}

    return game_result, game_infos
