import unittest
from dubito.hand import Hand
from dubito.handlers import GameHandler, StatsHandler, generate_player_data
from dubito.core_game import create_deck, assign_cards, initialize, dubito
from bots.rule_based import AlwaysTruthful, MrDoubt, MrNoDoubt, RandomBoi


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

    def test_joker_mixed_with_wrong_cards_is_still_honest(self):
        gh, _ = _make_game()
        gh.set_current_number(5)
        gh.set_board_cards([0, 3])  # 3 ≠ 5 but joker is present
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
        for _ in range(10):
            result, _ = dubito(
                all_players=[AlwaysTruthful(1), MrNoDoubt(2), MrDoubt(3), RandomBoi(4)],
                shuffle_players=True,
                n_jollies=2,
            )
            self.assertEqual(len(result['winners']), 1)

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
            self.assertEqual(len(result['winners']), 1)


# ---------------------------------------------------------------------------
# Full game smoke test
# ---------------------------------------------------------------------------

class TestFullGame(unittest.TestCase):

    def test_always_one_winner(self):
        for _ in range(20):
            result, _ = dubito(
                all_players=[AlwaysTruthful(1), MrNoDoubt(2), MrDoubt(3), RandomBoi(4)],
            )
            self.assertEqual(len(result['winners']), 1)

    def test_winner_not_in_losers(self):
        result, _ = dubito(
            all_players=[AlwaysTruthful(1), MrNoDoubt(2), MrDoubt(3), RandomBoi(4)],
        )
        winner_ids = {p.id for p in result['winners']}
        loser_ids = {p.id for p in result['losers']}
        self.assertTrue(winner_ids.isdisjoint(loser_ids))

    def test_all_players_accounted_for(self):
        players = [AlwaysTruthful(1), MrNoDoubt(2), MrDoubt(3), RandomBoi(4)]
        result, _ = dubito(all_players=players)
        total = len(result['winners']) + len(result['losers'])
        self.assertEqual(total, len(players))


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


if __name__ == '__main__':
    unittest.main()
