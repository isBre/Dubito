import unittest
from collections import Counter
from dubito.hand import Hand
from dubito.handlers import GameHandler, StatsHandler, generate_player_data
from dubito.core_game import (
    create_deck, assign_cards, initialize, dubito,
    has_n_equal_elements,
    _resolve_doubt, _handle_play, _process_end_of_turn,
)
from dubito.game_data import DoubtResolvedEvent, CardsPlayedEvent, DiscardEvent, PlayerWonEvent
from bots.manual.rule_based import AlwaysTruthful, MrDoubt, MrNoDoubt, RandomBoi


# ---------------------------------------------------------------------------
# Hand
# ---------------------------------------------------------------------------

class TestHand(unittest.TestCase):

    def test_pick_exact_amount(self):
        h = Hand([1, 1, 2, 3])
        picked = h.pick(1, 2)
        self.assertEqual(picked, [1, 1])
        self.assertEqual(sorted(h.hand), [2, 3])

    def test_pick_removes_from_hand(self):
        h = Hand([5, 5, 5])
        h.pick(5, 2)
        self.assertEqual(h.hand, [5])

    def test_pick_all(self):
        h = Hand([3, 3, 3, 7])
        picked = h.pick_all(3)
        self.assertEqual(picked, [3, 3, 3])
        self.assertEqual(h.hand, [7])

    def test_pick_random_reduces_hand(self):
        h = Hand([1, 2, 3, 4, 5])
        picked = h.pick_random(3)
        self.assertEqual(len(picked), 3)
        self.assertEqual(len(h.hand), 2)

    def test_discard_four_of_a_kind(self):
        h = Hand([1, 1, 1, 1, 2, 3])
        discarded = h.discard(amount=4)
        self.assertIn(1, discarded)
        self.assertNotIn(1, h.hand)

    def test_discard_does_not_remove_joker(self):
        # Jokers are value 0; at most 2 exist so discard(4) never removes them
        h = Hand([0, 0, 1, 1, 1, 1])
        discarded = h.discard(amount=4)
        self.assertIn(1, discarded)
        self.assertIn(0, h.hand)
        self.assertEqual(h.hand.count(0), 2)

    def test_add_sorts_hand(self):
        h = Hand([3, 5])
        h.add([1, 4])
        self.assertEqual(h.hand, [1, 3, 4, 5])

    def test_count(self):
        h = Hand([2, 2, 2, 5])
        self.assertEqual(h.count(2), 3)
        self.assertEqual(h.count(5), 1)
        self.assertEqual(h.count(9), 0)

    def test_has(self):
        h = Hand([7, 8])
        self.assertTrue(h.has(7))
        self.assertFalse(h.has(1))

    def test_len(self):
        h = Hand([1, 2, 3])
        self.assertEqual(len(h), 3)

    def test_pick_most(self):
        h = Hand([1, 2, 2, 2, 3])
        picked = h.pick_most()
        self.assertEqual(picked, [2, 2, 2])
        self.assertEqual(sorted(h.hand), [1, 3])


# ---------------------------------------------------------------------------
# Deck creation
# ---------------------------------------------------------------------------

class TestCreateDeck(unittest.TestCase):

    def test_standard_deck_size(self):
        deck = create_deck(deck_size=14, n_jollies=0)
        self.assertEqual(len(deck), 52)  # 13 numbers × 4

    def test_each_card_appears_four_times(self):
        deck = create_deck(deck_size=14, n_jollies=0)
        for n in range(1, 14):
            self.assertEqual(deck.count(n), 4)

    def test_jokers_added(self):
        deck = create_deck(deck_size=14, n_jollies=2)
        self.assertEqual(deck.count(0), 2)
        self.assertEqual(len(deck), 54)

    def test_no_jokers_by_default_is_zero(self):
        deck = create_deck(deck_size=14, n_jollies=0)
        self.assertNotIn(0, deck)


# ---------------------------------------------------------------------------
# GameHandler — is_honest / joker mechanic
# ---------------------------------------------------------------------------

def _make_game(n_players=4):
    players = [MrNoDoubt(i) for i in range(n_players)]
    return GameHandler(all_players=players, deck_size=14), players


class TestIsHonest(unittest.TestCase):

    def test_honest_when_cards_match(self):
        gh, _ = _make_game()
        gh.set_current_number(5)
        gh.set_board_cards([5, 5])
        self.assertTrue(gh.is_honest())

    def test_dishonest_when_cards_dont_match(self):
        gh, _ = _make_game()
        gh.set_current_number(5)
        gh.set_board_cards([5, 3])
        self.assertFalse(gh.is_honest())

    def test_joker_alone_is_honest(self):
        gh, _ = _make_game()
        gh.set_current_number(5)
        gh.set_board_cards([0])
        self.assertTrue(gh.is_honest())

    def test_joker_with_wrong_card_is_dishonest(self):
        # is_honest() checks each card individually: a joker protects its own
        # slot but a non-matching non-joker card still makes the play dishonest.
        # The whole-play joker protection is handled separately via jokers_in_latest().
        gh, _ = _make_game()
        gh.set_current_number(5)
        gh.set_board_cards([0, 3])  # joker OK, but 3 ≠ 5
        self.assertFalse(gh.is_honest())

    def test_joker_with_matching_card_is_honest(self):
        gh, _ = _make_game()
        gh.set_current_number(5)
        gh.set_board_cards([0, 5])  # joker + correct card
        self.assertTrue(gh.is_honest())

    def test_jokers_in_latest_returns_jokers(self):
        gh, _ = _make_game()
        gh.set_board_cards([0, 5, 0])
        self.assertEqual(gh.jokers_in_latest(), [0, 0])

    def test_jokers_in_latest_empty_when_none(self):
        gh, _ = _make_game()
        gh.set_board_cards([5, 5])
        self.assertEqual(gh.jokers_in_latest(), [])


# ---------------------------------------------------------------------------
# Joker mechanic end-to-end (via dubito)
# ---------------------------------------------------------------------------

class TestJokerMechanic(unittest.TestCase):

    def test_game_completes_with_jokers(self):
        # Game ends when 2 players remain → exactly 2 losers
        for _ in range(10):
            result, _ = dubito(
                all_players=[AlwaysTruthful(1), MrNoDoubt(2), MrDoubt(3), RandomBoi(4)],
                shuffle_players=True,
                n_jollies=2,
            )
            self.assertEqual(len(result['losers']), 2)

    def test_joker_event_appears_in_logs(self):
        # MrDoubt always doubts, RandomBoi bluffs randomly — joker events are frequent
        found = False
        for _ in range(300):
            _, infos = dubito(
                all_players=[MrDoubt(1), RandomBoi(2), MrDoubt(3), RandomBoi(4)],
                shuffle_players=False,
                n_jollies=2,
            )
            if 'Joker revealed' in infos['logs']:
                found = True
                break
        self.assertTrue(found, "Joker mechanic never triggered in 300 games")

    def test_game_completes_without_jokers(self):
        for _ in range(10):
            result, _ = dubito(
                all_players=[AlwaysTruthful(1), MrNoDoubt(2), MrDoubt(3), RandomBoi(4)],
                shuffle_players=True,
                n_jollies=0,
            )
            self.assertEqual(len(result['losers']), 2)


# ---------------------------------------------------------------------------
# Full game smoke test
# ---------------------------------------------------------------------------

class TestFullGame(unittest.TestCase):

    def test_exactly_two_losers(self):
        # Game ends when 2 players remain — both are losers.
        for _ in range(20):
            result, _ = dubito(
                all_players=[AlwaysTruthful(1), MrNoDoubt(2), MrDoubt(3), RandomBoi(4)],
            )
            self.assertEqual(len(result['losers']), 2)

    def test_n_minus_two_winners(self):
        players = [AlwaysTruthful(1), MrNoDoubt(2), MrDoubt(3), RandomBoi(4)]
        for _ in range(10):
            result, _ = dubito(all_players=list(players))
            self.assertEqual(len(result['winners']), len(players) - 2)

    def test_winner_not_in_losers(self):
        result, _ = dubito(
            all_players=[AlwaysTruthful(1), MrNoDoubt(2), MrDoubt(3), RandomBoi(4)],
        )
        winner_ids = {p.id for p in result['winners']}
        loser_ids  = {p.id for p in result['losers']}
        self.assertTrue(winner_ids.isdisjoint(loser_ids))

    def test_all_players_accounted_for(self):
        players = [AlwaysTruthful(1), MrNoDoubt(2), MrDoubt(3), RandomBoi(4)]
        result, _ = dubito(all_players=players)
        total = len(result['winners']) + len(result['losers'])
        self.assertEqual(total, len(players))

    def test_winners_ordered_by_finish(self):
        # winners[0] emptied their hand first; the list must be a permutation of the players
        players = [AlwaysTruthful(1), MrNoDoubt(2), MrDoubt(3), RandomBoi(4)]
        result, _ = dubito(all_players=list(players))
        winner_ids = [p.id for p in result['winners']]
        # All winner ids are distinct
        self.assertEqual(len(winner_ids), len(set(winner_ids)))

    def test_turn_cap_terminates_game(self):
        # With max_turns=1 the game must terminate immediately and account for all players.
        players = [AlwaysTruthful(1), MrNoDoubt(2), MrDoubt(3), RandomBoi(4)]
        result, infos = dubito(all_players=list(players), max_turns=1)
        total = len(result['winners']) + len(result['losers'])
        self.assertEqual(total, len(players))
        self.assertIn('Turn limit', infos['logs'])

    def test_player_sizes_vary(self):
        for n in range(3, 8):
            ps = [RandomBoi(i) for i in range(1, n + 1)]
            result, _ = dubito(all_players=ps)
            self.assertEqual(len(result['winners']) + len(result['losers']), n)
            self.assertEqual(len(result['losers']), 2)
            self.assertEqual(len(result['winners']), n - 2)

    def test_no_crash_on_correct_doubt_after_win(self):
        # Regression: correct_doubt=True reuses prev_player across loop iterations.
        # If prev_player won in the previous won-phase, set_winners must not fire again.
        for _ in range(200):
            result, _ = dubito(
                all_players=[MrDoubt(1), RandomBoi(2), MrDoubt(3), RandomBoi(4)],
            )
            total = len(result['winners']) + len(result['losers'])
            self.assertEqual(total, 4)


# ---------------------------------------------------------------------------
# Board state
# ---------------------------------------------------------------------------

class TestBoardState(unittest.TestCase):

    def test_is_first_hand_true_when_empty(self):
        gh, _ = _make_game()
        self.assertTrue(gh.is_first_hand())

    def test_is_first_hand_false_after_play(self):
        gh, _ = _make_game()
        gh.set_board_cards([5])
        self.assertFalse(gh.is_first_hand())

    def test_board_accumulates_across_plays(self):
        gh, _ = _make_game()
        gh.set_board_cards([1, 2])
        gh.set_board_cards([3])
        self.assertEqual(sorted(gh.get_board()), [1, 2, 3])
        self.assertEqual(gh.n_cards_board(), 3)

    def test_latests_updated_to_most_recent_play(self):
        gh, _ = _make_game()
        gh.set_board_cards([1, 2])
        gh.set_board_cards([7, 8])
        self.assertEqual(gh.get_latest_played_cards(), [7, 8])

    def test_reset_board_clears_everything(self):
        gh, _ = _make_game()
        gh.set_current_number(5)
        gh.set_board_cards([5, 5])
        gh.turn.streak = 3
        gh.reset_board()
        self.assertEqual(gh.get_board(), [])
        self.assertEqual(gh.get_current_number(), 0)
        self.assertEqual(gh.get_latest_played_cards(), [])
        self.assertEqual(gh.turn.streak, 0)

    def test_set_discarded_cards_removes_from_availables(self):
        gh, _ = _make_game()
        self.assertIn(5, gh.board.availables)
        gh.set_discarded_cards([5])
        self.assertNotIn(5, gh.board.availables)

    def test_set_discarded_cards_leaves_others_intact(self):
        gh, _ = _make_game()
        gh.set_discarded_cards([5])
        for n in range(1, 14):
            if n != 5:
                self.assertIn(n, gh.board.availables)


# ---------------------------------------------------------------------------
# Turn cycling
# ---------------------------------------------------------------------------

class TestTurnCycling(unittest.TestCase):

    def test_next_turn_returns_correct_players(self):
        gh, players = _make_game(n_players=4)
        prev, this = gh.next_turn()
        # Initial position is len-1, so first next_turn wraps to position 0 (prev=last, this=first)
        self.assertIn(prev, players)
        self.assertIn(this, players)
        self.assertNotEqual(prev.id, this.id)

    def test_turn_cycles_through_all_players(self):
        gh, players = _make_game(n_players=3)
        seen = set()
        for _ in range(3):
            _, this = gh.next_turn()
            seen.add(this.id)
        self.assertEqual(len(seen), 3)

    def test_streak_increments_each_turn(self):
        gh, _ = _make_game()
        gh.next_turn()
        gh.next_turn()
        self.assertEqual(gh.turn.streak, 2)

    def test_streak_resets_on_board_reset(self):
        gh, _ = _make_game()
        gh.next_turn()
        gh.next_turn()
        gh.reset_board()
        self.assertEqual(gh.turn.streak, 0)


# ---------------------------------------------------------------------------
# Doubt card distribution
# ---------------------------------------------------------------------------

class TestDoubtCardDistribution(unittest.TestCase):

    def _setup_doubt(self):
        """Returns (game_handler, doubter_player, bluffer_player) with 3 cards on the board."""
        gh, players = _make_game(n_players=3)
        doubter, bluffer = players[0], players[1]
        gh.set_current_number(5)
        gh.set_board_cards([5, 3, 3])   # bluff: 3s declared as 5s
        return gh, doubter, bluffer

    def test_wrong_doubt_gives_board_cards_to_doubter(self):
        gh, doubter, _ = _make_game(n_players=3)[0], _make_game(n_players=3)[1][0], None
        gh, players = _make_game(n_players=3)
        doubter = players[0]
        gh.set_current_number(7)
        gh.set_board_cards([7, 7])   # honest play
        cards_before = len(doubter.cards)
        doubter.add_cards(gh.get_board())
        gh.reset_board()
        self.assertEqual(len(doubter.cards), cards_before + 2)
        self.assertEqual(gh.get_board(), [])

    def test_correct_doubt_gives_board_cards_to_bluffer(self):
        gh, players = _make_game(n_players=3)
        bluffer = players[1]
        gh.set_current_number(7)
        gh.set_board_cards([7, 3])   # bluff
        cards_before = len(bluffer.cards)
        bluffer.add_cards(gh.get_board())
        gh.reset_board()
        self.assertEqual(len(bluffer.cards), cards_before + 2)
        self.assertEqual(gh.get_board(), [])

    def test_joker_doubt_discards_joker_doubter_gets_rest(self):
        gh, players = _make_game(n_players=3)
        doubter = players[0]
        # Accumulate 2 regular cards from a previous play, then joker play
        gh.set_board_cards([5, 5])        # prior round cards
        gh.set_board_cards([0, 3])        # joker + bluff card (latest)
        jokers = gh.jokers_in_latest()    # [0]
        board = list(gh.get_board())      # [5, 5, 0, 3]
        for j in jokers:
            board.remove(j)               # discard joker → [5, 5, 3]
        cards_before = len(doubter.cards)
        doubter.add_cards(board)
        self.assertEqual(len(doubter.cards), cards_before + 3)  # gets 3, not 4


# ---------------------------------------------------------------------------
# Card distribution (assign_cards / initialize)
# ---------------------------------------------------------------------------

class TestCardDistribution(unittest.TestCase):

    def test_assign_cards_distributes_all(self):
        players = [MrNoDoubt(i) for i in range(4)]
        deck = list(range(52))  # arbitrary 52 cards
        assign_cards(deck, players)
        total = sum(len(p.cards) for p in players)
        self.assertEqual(total, 52)

    def test_assign_cards_round_robin(self):
        players = [MrNoDoubt(i) for i in range(4)]
        assign_cards([1, 2, 3, 4, 5, 6, 7, 8], players)
        # Each player should have exactly 2 cards
        for p in players:
            self.assertEqual(len(p.cards), 2)

    def test_initialize_no_player_starts_with_four_equal(self):
        for _ in range(10):
            players = [MrNoDoubt(i) for i in range(4)]
            initialize(players, deck_size=14)
            for p in players:
                counts = p.cards.count_all()
                self.assertFalse(any(v >= 4 for v in counts.values()))

    def test_initialize_distributes_full_deck(self):
        players = [MrNoDoubt(i) for i in range(4)]
        initialize(players, deck_size=14, n_jollies=2)
        total = sum(len(p.cards) for p in players)
        self.assertEqual(total, 54)  # 52 regular + 2 jokers


# ---------------------------------------------------------------------------
# Winners / playing players
# ---------------------------------------------------------------------------

class TestWinners(unittest.TestCase):

    def test_set_winners_removes_from_playing(self):
        gh, players = _make_game(n_players=4)
        gh.next_turn()  # set gh.players.this
        winner = players[0]
        gh.players.this = players[1]  # ensure this != winner so position update works
        gh.set_winners(winner)
        self.assertNotIn(winner, gh.playing_players())
        self.assertIn(winner, gh.get_winners())

    def test_n_playing_players_decreases_after_win(self):
        gh, players = _make_game(n_players=4)
        gh.next_turn()
        gh.players.this = players[1]
        gh.set_winners(players[0])
        self.assertEqual(gh.n_playing_players(), 3)

    def test_winners_list_is_ordered(self):
        # Each successive set_winners call appends to the end of the winners list.
        gh, players = _make_game(n_players=4)
        gh.next_turn()
        gh.players.this = players[1]
        gh.set_winners(players[0])   # 1st place
        gh.players.this = players[2]
        gh.set_winners(players[1])   # 2nd place
        self.assertEqual(gh.get_winners(), [players[0], players[1]])


# ---------------------------------------------------------------------------
# Stats tracking
# ---------------------------------------------------------------------------

class TestStatsTracking(unittest.TestCase):

    def test_play_turns_and_cards_counted(self):
        # AlwaysTruthful never doubts, so play_turns must be positive after a game.
        players = [AlwaysTruthful(1), MrNoDoubt(2), MrDoubt(3), RandomBoi(4)]
        _, infos = dubito(all_players=list(players))
        stats = infos['stats'].data
        for p in players:
            s = stats[p.id]
            self.assertGreaterEqual(s['play_turns'], 0)
            self.assertGreaterEqual(s['total_cards_played'], 0)
            # play_turns ≤ turns (doubts also count as turns)
            self.assertLessEqual(s['play_turns'], s['turns'])

    def test_doubts_counted_for_mr_doubt(self):
        players = [MrDoubt(1), MrNoDoubt(2), MrNoDoubt(3)]
        _, infos = dubito(all_players=list(players), shuffle_players=False)
        stats = infos['stats'].data
        # MrDoubt always doubts when not first hand; must have at least one doubt
        self.assertGreater(stats[1]['doubts'], 0)

    def test_bluffs_tracked(self):
        # RandomBoi bluffs randomly; across enough games at least one bluff occurs.
        found = False
        for _ in range(50):
            players = [RandomBoi(1), RandomBoi(2), RandomBoi(3)]
            _, infos = dubito(all_players=list(players))
            stats = infos['stats'].data
            if any(stats[p.id]['bluffs'] > 0 for p in players):
                found = True
                break
        self.assertTrue(found, "No bluffs recorded across 50 games with RandomBoi")

    def test_successful_doubts_lte_doubts(self):
        for _ in range(10):
            players = [MrDoubt(1), RandomBoi(2), MrDoubt(3), RandomBoi(4)]
            _, infos = dubito(all_players=list(players))
            stats = infos['stats'].data
            for p in players:
                s = stats[p.id]
                self.assertLessEqual(s['successful_doubts'], s['doubts'])

    def test_not_first_turns_lte_turns(self):
        players = [AlwaysTruthful(1), MrNoDoubt(2), MrDoubt(3), RandomBoi(4)]
        _, infos = dubito(all_players=list(players))
        stats = infos['stats'].data
        for p in players:
            s = stats[p.id]
            self.assertLessEqual(s['not_first_turns'], s['turns'])

    def test_total_cards_played_ge_play_turns(self):
        # Each play turn places at least 1 card, so total_cards_played >= play_turns.
        players = [AlwaysTruthful(1), MrNoDoubt(2), MrDoubt(3), RandomBoi(4)]
        _, infos = dubito(all_players=list(players))
        stats = infos['stats'].data
        for p in players:
            s = stats[p.id]
            self.assertGreaterEqual(s['total_cards_played'], s['play_turns'])


# ---------------------------------------------------------------------------
# Turn order after a player wins (soft win)
# ---------------------------------------------------------------------------

class TestTurnOrderAfterWin(unittest.TestCase):
    """
    Verify that when a player is eliminated mid-game the remaining players
    cycle correctly and the winner never appears as prev or this again.

    Initial turn.position = len(players)-1 = 3, so next_turn() calls produce:
      call #1 → prev=p3, this=p0
      call #2 → prev=p0, this=p1
      call #3 → prev=p1, this=p2   ← p2 is "this"  (bot3 in user scenario)
      call #4 → prev=p2, this=p3   ← p2 is "prev"
    """

    def _advance(self, gh, n):
        for _ in range(n):
            gh.next_turn()

    # ------------------------------------------------------------------
    # Core scenario: [bot1 bot2 bot3 bot4] → bot3 wins → bot1 bot2 bot4
    # ------------------------------------------------------------------

    def test_bot3_wins_as_this_player_cycle_is_bot1_bot2_bot4(self):
        """bot3 wins during their own turn (this_player); remaining cycle: bot1, bot2, bot4."""
        gh, players = _make_game(n_players=4)
        # After 3 next_turn() calls: this=players[2] (bot3), prev=players[1]
        self._advance(gh, 3)
        self.assertEqual(gh.players.this.id, players[2].id)

        gh.set_winners(players[2])
        self.assertNotIn(players[2], gh.playing_players())

        seen = set()
        for _ in range(9):  # 3 remaining players × 3 full cycles
            _, this = gh.next_turn()
            seen.add(this.id)

        self.assertNotIn(players[2].id, seen)
        self.assertEqual(seen, {players[0].id, players[1].id, players[3].id})

    def test_bot3_wins_as_prev_player_cycle_is_bot1_bot2_bot4(self):
        """bot3 wins at end of their turn (prev_player); remaining cycle: bot1, bot2, bot4."""
        gh, players = _make_game(n_players=4)
        # After 4 next_turn() calls: prev=players[2] (bot3), this=players[3]
        self._advance(gh, 4)
        self.assertEqual(gh.players.prev.id, players[2].id)

        gh.set_winners(players[2])
        self.assertNotIn(players[2], gh.playing_players())

        seen = set()
        for _ in range(9):
            _, this = gh.next_turn()
            seen.add(this.id)

        self.assertNotIn(players[2].id, seen)
        self.assertEqual(seen, {players[0].id, players[1].id, players[3].id})

    # ------------------------------------------------------------------
    # Winner never appears as prev either
    # ------------------------------------------------------------------

    def test_winner_never_appears_as_prev_or_this(self):
        gh, players = _make_game(n_players=4)
        self._advance(gh, 3)
        winner = gh.players.this

        gh.set_winners(winner)

        for _ in range(9):
            prev, this = gh.next_turn()
            self.assertNotEqual(prev.id, winner.id)
            self.assertNotEqual(this.id, winner.id)

    # ------------------------------------------------------------------
    # set_winners() on this_player must not crash
    # ------------------------------------------------------------------

    def test_set_winners_this_player_does_not_crash(self):
        gh, players = _make_game(n_players=4)
        self._advance(gh, 3)
        this = gh.players.this
        gh.set_winners(this)  # previously raised ValueError
        self.assertNotIn(this, gh.playing_players())
        self.assertIn(this, gh.get_winners())

    # ------------------------------------------------------------------
    # turn.position stays in-bounds across multiple eliminations
    # ------------------------------------------------------------------

    def test_position_valid_after_successive_eliminations(self):
        gh, players = _make_game(n_players=4)
        self._advance(gh, 2)
        gh.set_winners(players[1])   # remove p1 while p1 is this

        self._advance(gh, 1)
        gh.set_winners(players[3])   # remove p3

        # 2 players left; all next_turn() calls must succeed and stay in-bounds
        for _ in range(4):
            prev, this = gh.next_turn()
            self.assertIn(prev, gh.playing_players() + gh.get_winners())
            self.assertIn(this, gh.playing_players())

    # ------------------------------------------------------------------
    # Win detection fires for this_player (discard-phase win)
    # ------------------------------------------------------------------

    def test_win_detection_catches_this_player(self):
        """set_winners(this_player) reduces playing count — confirms engine can handle it."""
        gh, players = _make_game(n_players=4)
        self._advance(gh, 3)
        this = gh.players.this
        n_before = gh.n_playing_players()
        gh.set_winners(this)
        self.assertEqual(gh.n_playing_players(), n_before - 1)

    # ------------------------------------------------------------------
    # Regression: correct_doubt renamed to replay_turn
    # ------------------------------------------------------------------

    def test_no_crash_on_replay_turn_after_soft_win(self):
        for _ in range(200):
            result, _ = dubito(
                all_players=[MrDoubt(1), RandomBoi(2), MrDoubt(3), RandomBoi(4)],
            )
            total = len(result['winners']) + len(result['losers'])
            self.assertEqual(total, 4)


# ---------------------------------------------------------------------------
# Two-loser rule: game always ends with exactly 2 losers
# ---------------------------------------------------------------------------

class TestTwoLoserRule(unittest.TestCase):

    def test_three_players_one_winner_two_losers_no_soft_wins(self):
        # With 3 players: first to empty hand wins, the remaining 2 both lose.
        # Soft wins are impossible — there is no middle position.
        for _ in range(30):
            result, _ = dubito(
                all_players=[AlwaysTruthful(1), MrNoDoubt(2), RandomBoi(3)],
            )
            self.assertEqual(len(result['winners']), 1)
            self.assertEqual(len(result['losers']), 2)

    def test_four_players_two_winners_two_losers(self):
        # 1 hard win + 1 soft win + 2 losses
        for _ in range(20):
            result, _ = dubito(
                all_players=[AlwaysTruthful(1), MrNoDoubt(2), MrDoubt(3), RandomBoi(4)],
            )
            self.assertEqual(len(result['winners']), 2)
            self.assertEqual(len(result['losers']), 2)

    def test_five_players_three_winners_two_losers(self):
        # 1 hard win + 2 soft wins + 2 losses
        for _ in range(10):
            result, _ = dubito(
                all_players=[RandomBoi(i) for i in range(1, 6)],
            )
            self.assertEqual(len(result['winners']), 3)
            self.assertEqual(len(result['losers']), 2)

    def test_losers_are_disjoint_from_winners(self):
        for _ in range(20):
            result, _ = dubito(
                all_players=[AlwaysTruthful(1), MrNoDoubt(2), MrDoubt(3), RandomBoi(4)],
            )
            winner_ids = {p.id for p in result['winners']}
            loser_ids  = {p.id for p in result['losers']}
            self.assertTrue(winner_ids.isdisjoint(loser_ids))


# ---------------------------------------------------------------------------
# has_n_equal_elements
# ---------------------------------------------------------------------------

class TestHasNEqualElements(unittest.TestCase):

    def test_returns_true_when_count_equals_n(self):
        c = Counter({5: 4, 3: 2})
        self.assertTrue(has_n_equal_elements(c, 4))

    def test_returns_true_when_count_exceeds_n(self):
        c = Counter({7: 5})
        self.assertTrue(has_n_equal_elements(c, 4))

    def test_returns_false_when_all_counts_below_n(self):
        c = Counter({1: 3, 2: 2, 3: 1})
        self.assertFalse(has_n_equal_elements(c, 4))

    def test_returns_false_for_empty_counter(self):
        self.assertFalse(has_n_equal_elements(Counter(), 4))

    def test_exactly_one_qualifying_card(self):
        c = Counter({1: 1, 2: 1, 3: 4})
        self.assertTrue(has_n_equal_elements(c, 4))
        self.assertFalse(has_n_equal_elements(c, 5))


# ---------------------------------------------------------------------------
# _resolve_doubt
# ---------------------------------------------------------------------------

def _setup_game_for_doubt(board_cards, current_number=5, n_players=3):
    players = [MrNoDoubt(i) for i in range(n_players)]
    gh = GameHandler(all_players=players, deck_size=14)
    stats = StatsHandler(all_players=players)
    gh.set_current_number(current_number)
    gh.set_board_cards(board_cards)
    gh.players.prev = players[0]
    gh.players.this = players[1]
    return gh, stats, players


class TestResolveDoubt(unittest.TestCase):

    def test_honest_play_gives_cards_to_doubter(self):
        gh, stats, players = _setup_game_for_doubt([5, 5])
        doubter, bluffer = players[1], players[0]
        cards_before = len(doubter.cards)
        replay, log = _resolve_doubt(gh, doubter, bluffer, stats)
        self.assertFalse(replay)
        self.assertEqual(len(doubter.cards), cards_before + 2)
        self.assertEqual(gh.get_board(), [])

    def test_dishonest_play_gives_cards_to_bluffer(self):
        gh, stats, players = _setup_game_for_doubt([5, 3])
        doubter, bluffer = players[1], players[0]
        cards_before = len(bluffer.cards)
        replay, log = _resolve_doubt(gh, doubter, bluffer, stats)
        self.assertTrue(replay)
        self.assertEqual(len(bluffer.cards), cards_before + 2)
        self.assertEqual(gh.get_board(), [])

    def test_joker_honest_discards_joker_doubter_gets_rest(self):
        gh, stats, players = _setup_game_for_doubt([0, 5])
        doubter, bluffer = players[1], players[0]
        cards_before = len(doubter.cards)
        replay, log = _resolve_doubt(gh, doubter, bluffer, stats)
        self.assertFalse(replay)
        self.assertEqual(len(doubter.cards), cards_before + 1)  # joker discarded, gets 1 card
        self.assertIn('Joker revealed', log)

    def test_board_reset_after_doubt(self):
        gh, stats, players = _setup_game_for_doubt([5, 5])
        _resolve_doubt(gh, players[1], players[0], stats)
        self.assertEqual(gh.get_board(), [])
        self.assertEqual(gh.get_current_number(), 0)

    def test_doubt_event_appended(self):
        gh, stats, players = _setup_game_for_doubt([5, 3])
        _resolve_doubt(gh, players[1], players[0], stats)
        self.assertTrue(any(isinstance(e, DoubtResolvedEvent) for e in gh.history))

    def test_stats_doubts_incremented(self):
        gh, stats, players = _setup_game_for_doubt([5, 5])
        _resolve_doubt(gh, players[1], players[0], stats)
        self.assertEqual(stats.data[players[1].id]['doubts'], 1)

    def test_stats_honesty_incremented_on_honest_play(self):
        gh, stats, players = _setup_game_for_doubt([5, 5])
        _resolve_doubt(gh, players[1], players[0], stats)
        self.assertEqual(stats.data[players[0].id]['honest_times'], 1)

    def test_stats_dishonesty_and_successful_doubt_incremented(self):
        gh, stats, players = _setup_game_for_doubt([5, 3])
        _resolve_doubt(gh, players[1], players[0], stats)
        self.assertEqual(stats.data[players[0].id]['dishonest_times'], 1)
        self.assertEqual(stats.data[players[1].id]['successful_doubts'], 1)


# ---------------------------------------------------------------------------
# _handle_play
# ---------------------------------------------------------------------------

def _setup_game_for_play(n_players=3):
    players = [MrNoDoubt(i) for i in range(n_players)]
    gh = GameHandler(all_players=players, deck_size=14)
    stats = StatsHandler(all_players=players)
    gh.players.prev = players[0]
    gh.players.this = players[1]
    return gh, stats, players


class TestHandlePlay(unittest.TestCase):

    def test_first_hand_sets_current_number(self):
        from dubito.game_data import TurnOutput
        gh, stats, players = _setup_game_for_play()
        output = TurnOutput(doubt=False, number=7, cards=[7])
        _handle_play(gh, players[1], output, stats)
        self.assertEqual(gh.get_current_number(), 7)

    def test_cards_placed_on_board(self):
        from dubito.game_data import TurnOutput
        gh, stats, players = _setup_game_for_play()
        gh.set_current_number(3)
        gh.set_board_cards([3])  # simulate non-first-hand
        output = TurnOutput(doubt=False, number=None, cards=[3, 3])
        _handle_play(gh, players[1], output, stats)
        self.assertIn(3, gh.get_board())
        self.assertEqual(gh.n_cards_board(), 3)

    def test_cards_played_event_appended(self):
        from dubito.game_data import TurnOutput
        gh, stats, players = _setup_game_for_play()
        output = TurnOutput(doubt=False, number=5, cards=[5])
        _handle_play(gh, players[1], output, stats)
        self.assertTrue(any(isinstance(e, CardsPlayedEvent) for e in gh.history))

    def test_stats_cards_played_tracked(self):
        from dubito.game_data import TurnOutput
        gh, stats, players = _setup_game_for_play()
        output = TurnOutput(doubt=False, number=5, cards=[5, 5])
        _handle_play(gh, players[1], output, stats)
        self.assertEqual(stats.data[players[1].id]['total_cards_played'], 2)
        self.assertEqual(stats.data[players[1].id]['play_turns'], 1)

    def test_bluff_tracked_in_stats(self):
        from dubito.game_data import TurnOutput
        gh, stats, players = _setup_game_for_play()
        gh.set_current_number(5)
        gh.set_board_cards([5])  # move past first hand
        output = TurnOutput(doubt=False, number=None, cards=[3])  # 3 ≠ 5 → bluff
        _handle_play(gh, players[1], output, stats)
        self.assertEqual(stats.data[players[1].id]['bluffs'], 1)


# ---------------------------------------------------------------------------
# _process_end_of_turn
# ---------------------------------------------------------------------------

class TestProcessEndOfTurn(unittest.TestCase):

    def test_winner_detected_when_player_has_no_cards(self):
        players = [MrNoDoubt(i) for i in range(3)]
        gh = GameHandler(all_players=players, deck_size=14)
        gh.next_turn()
        gh.players.this = players[1]
        # give player[0] no cards (hand is already empty from GameHandler init)
        log = _process_end_of_turn(gh)
        # players[0] starts with empty hand so they should be detected as winners
        self.assertIn(players[0], gh.get_winners())

    def test_discard_event_appended_when_four_of_a_kind(self):
        players = [MrNoDoubt(i) for i in range(3)]
        gh = GameHandler(all_players=players, deck_size=14)
        gh.next_turn()
        gh.players.this = players[1]
        players[0].add_cards([9, 9, 9, 9])
        _process_end_of_turn(gh)
        self.assertTrue(any(isinstance(e, DiscardEvent) for e in gh.history))

    def test_player_won_event_appended_when_no_cards(self):
        players = [MrNoDoubt(i) for i in range(3)]
        gh = GameHandler(all_players=players, deck_size=14)
        gh.next_turn()
        gh.players.this = players[1]
        _process_end_of_turn(gh)
        self.assertTrue(any(isinstance(e, PlayerWonEvent) for e in gh.history))

    def test_no_discard_event_when_no_four_of_a_kind(self):
        players = [MrNoDoubt(i) for i in range(3)]
        gh = GameHandler(all_players=players, deck_size=14)
        gh.next_turn()
        gh.players.this = players[1]
        players[0].add_cards([1, 2, 3])
        _process_end_of_turn(gh)
        self.assertFalse(any(isinstance(e, DiscardEvent) for e in gh.history))


if __name__ == '__main__':
    unittest.main()
