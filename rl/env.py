"""
DubitoEnv — single-agent Gymnasium wrapper around the Dubito game engine.

One episode = one complete game. The RL agent controls one player;
all other seats are filled with randomly sampled rule-based opponents.
The game advances automatically through opponents' turns; step() is only
called when it is the RL agent's turn.

─── Action space (Discrete 7) ───────────────────────────────────────────────
  0  Doubt           challenge previous player
                     → illegal on first hand: remapped to Honest-1
  1  Honest, 1 card  play 1 matching card (+ joker if short)
                     → forced bluff if 0 matching and 0 jokers
  2  Honest, 2 cards play up to 2 matching cards + jokers (max 3 total)
  3  Honest, 3 cards play up to 3 matching cards + jokers  (hard cap: 3)
  4  Bluff,  1 card  play 1 non-matching card
  5  Bluff,  2 cards play 2 non-matching cards
  6  Bluff,  3 cards play 3 non-matching cards

  Jokers (value 0) are wildcards: they count as honest in any play.
  Honest actions fill shortfall with jokers. Bluff actions skip jokers.
  You can NEVER play more than 3 cards in a single turn.

─── Observation space (Box float32, shape=(60,)) ────────────────────────────
  Continuous features are left as raw integers — VecNormalize in train.py
  handles normalisation based on running game statistics. Binary and one-hot
  features stay in {0, 1} and are excluded from VecNormalize.

  [0:14]   hand card counts, raw integers 0..4
           (index 0 = joker count, 1..13 = face-value counts)
  [14]     n_matching   raw count of cards matching current declared number (0..3)
  [15]     n_jokers     raw joker count (0..2)
  [16]     is_first_hand        {0, 1}
  [17]     my_n_cards           raw integer 0..30
  [18]     board_cards          raw integer 0..30
  [19]     n_cards_played       raw integer 0..3  (last player's play size)
  [20]     jokers_in_last_play  {0, 1}
  [21]     streak               raw integer 0..30
  [22]     n_players            raw integer 2..8
  [23:37]  current_number one-hot (14 dims, values 0..13)  {0, 1}
  [37:50]  available_numbers binary mask (13 dims, 1..13)  {0, 1}
  [50:55]  prev player: (n_cards, turns, doubt_rate, honesty_rate, caught_rate)
  [55:60]  next player: same

  Rates [50:60] are naturally in [0, 1] so they don't need VecNormalize.
"""

import random
import numpy as np
import gymnasium as gym
from gymnasium import spaces
from collections import Counter

from dubito.player import PlayerAI
from dubito.hand import Hand
from dubito.game_data import (
    TurnOutput, TurnData, GameStartEvent, CardsPlayedEvent,
    DoubtResolvedEvent, DiscardEvent, PlayerWonEvent,
    honest_times, dishonest_times, doubts_count, turns_count,
)
from dubito.handlers import GameHandler, generate_player_data
from dubito.core_game import initialize
import bots  # noqa: F401 — populates BotBase.registry
from bots.base import BotBase

# LLM bots are excluded: they require API access and are too slow for rollouts.
_LLM_BOTS = {'ClaudeBot', 'ChatGPTBot', 'ChatGPTThinkingBot', 'GeminiBot'}
OPPONENT_POOL = [cls for name, cls in BotBase.registry.items() if name not in _LLM_BOTS]

N_ACTIONS = 7
OBS_DIM   = 60
MAX_TURNS = 1_000

_PLAYER_STATS_HIGH = [30.0, 200.0, 1.0, 1.0, 1.0]  # n_cards, turns, doubt_r, honest_r, caught_r

_OBS_HIGH = np.array(
    [4.0] * 14 +
    [3.0, 2.0,
     1.0,
     30.0, 30.0, 3.0,
     1.0, 30.0, 8.0] +
    [1.0] * 14 +
    [1.0] * 13 +
    _PLAYER_STATS_HIGH * 2,
    dtype=np.float32,
)


# ── observation helpers ───────────────────────────────────────────────────────

def _player_stats_vec(player_id: int, n_cards: int, history: list) -> np.ndarray:
    """5-dim stats for a neighbouring player, derived from event history."""
    t = turns_count(player_id, history)
    d = doubts_count(player_id, history)
    h = honest_times(player_id, history)
    c = dishonest_times(player_id, history)
    t_safe = max(t, 1)
    plays_safe = max(t - d, 1)
    return np.array([
        float(n_cards),
        float(t),
        d / t_safe,     # doubt rate       ∈ [0, 1]
        h / t_safe,     # honesty rate     ∈ [0, 1]
        c / plays_safe, # caught-bluff rate ∈ [0, 1]
    ], dtype=np.float32)


def build_obs(
    turn_data: TurnData,
    hand: list[int],
    jokers_in_last_play: bool = False,
) -> np.ndarray:
    obs = np.zeros(OBS_DIM, dtype=np.float32)

    current_num = int(turn_data.current_number)

    for card in hand:
        if 0 <= card <= 13:
            obs[card] += 1.0

    n_jokers   = sum(1 for c in hand if c == 0)
    n_matching = sum(1 for c in hand if c == current_num) if current_num > 0 else 0

    obs[14] = float(n_matching)
    obs[15] = float(n_jokers)
    obs[16] = float(turn_data.board_cards == 0)
    obs[17] = float(len(turn_data.my_cards))
    obs[18] = float(turn_data.board_cards)
    obs[19] = float(turn_data.n_cards_played)
    obs[20] = float(jokers_in_last_play)
    obs[21] = float(turn_data.streak)
    obs[22] = float(turn_data.n_players)

    if 0 <= current_num <= 13:
        obs[23 + current_num] = 1.0

    for n in turn_data.playing_cards:
        if 1 <= n <= 13:
            obs[36 + n] = 1.0

    obs[50:55] = _player_stats_vec(
        turn_data.prev_player_id,
        turn_data.player_card_counts.get(turn_data.prev_player_id, 0),
        turn_data.history,
    )
    obs[55:60] = _player_stats_vec(
        turn_data.next_player_id,
        turn_data.player_card_counts.get(turn_data.next_player_id, 0),
        turn_data.history,
    )

    return obs


# ── action → TurnOutput ───────────────────────────────────────────────────────

def action_to_output(action: int, player: PlayerAI, turn_data: TurnData, is_first: bool) -> TurnOutput:
    """
    Map a discrete action (0-6) to a TurnOutput.
    Handles jokers, forced bluffs, and first-hand specifics.
    """
    hand        = list(player.cards.hand)
    current_num = int(turn_data.current_number)
    jokers      = [c for c in hand if c == 0]
    non_jokers  = [c for c in hand if c != 0]

    if action == 0 and is_first:
        action = 1

    if action == 0:
        return TurnOutput(doubt=True, number=None, cards=None)

    is_bluff = action >= 4
    qty      = action if not is_bluff else action - 3

    if is_first:
        if not is_bluff:
            counts = Counter(non_jokers)
            if counts:
                best_val, best_cnt = counts.most_common(1)[0]
                n_face = min(qty, 3, best_cnt)
                cards  = player.cards.pick(best_val, n_face)
                n_need = min(qty, 3) - len(cards)
                if n_need > 0 and jokers:
                    cards += player.cards.pick(0, min(n_need, len(jokers)))
                return TurnOutput(doubt=False, number=best_val, cards=cards)
            else:
                cards  = player.cards.pick(0, min(qty, len(jokers)))
                pool   = turn_data.playing_cards or list(range(1, 14))
                number = random.choice(pool)
                return TurnOutput(doubt=False, number=number, cards=cards)
        else:
            n     = min(qty, len(hand))
            cards = player.cards.pick_random(n)
            pool  = turn_data.playing_cards or list(range(1, 14))
            played_vals  = set(cards)
            mismatches   = [v for v in pool if v not in played_vals]
            number       = random.choice(mismatches) if mismatches else random.choice(pool)
            return TurnOutput(doubt=False, number=number, cards=cards)

    matching = [c for c in hand if c == current_num]

    if not is_bluff:
        if not matching and not jokers:
            n     = min(qty, 3, len(hand))
            cards = player.cards.pick_random(n)
        else:
            n_face = min(qty, 3, len(matching))
            cards  = player.cards.pick(current_num, n_face)
            n_need = min(qty, 3) - len(cards)
            if n_need > 0 and jokers:
                cards += player.cards.pick(0, min(n_need, len(jokers)))
        return TurnOutput(doubt=False, number=None, cards=cards)
    else:
        bluff_pool = [c for c in hand if c != current_num and c != 0]
        if bluff_pool:
            n     = min(qty, len(bluff_pool))
            cards = random.sample(bluff_pool, n)
            for c in cards:
                player.cards.hand.remove(c)
        else:
            n     = min(qty, len(hand))
            cards = player.cards.pick_random(n)
        return TurnOutput(doubt=False, number=None, cards=cards)


# ── environment ───────────────────────────────────────────────────────────────

class _RLPlayerProxy(PlayerAI):
    """
    Thin PlayerAI stub used inside game simulation.
    The env intercepts its turn before play() runs and stores
    the pending TurnData so step() can resolve the action.
    """
    def __init__(self, player_id: int):
        super().__init__(player_id)
        self._pending_turn: TurnData | None = None

    def play_first_turn(self, _):
        raise RuntimeError("intercepted by env — should never be called")

    def play_regular_turn(self, _):
        raise RuntimeError("intercepted by env — should never be called")


class DubitoEnv(gym.Env):
    """Single-agent Gymnasium environment for Dubito."""

    metadata = {"render_modes": []}

    def __init__(self, n_players: int | None = None, opponent_pool: list | None = None):
        super().__init__()
        self.action_space      = spaces.Discrete(N_ACTIONS)
        self.observation_space = spaces.Box(
            low=np.zeros(OBS_DIM, dtype=np.float32),
            high=_OBS_HIGH,
            dtype=np.float32,
        )

        self._n_players_fixed = n_players
        self._pool            = opponent_pool or OPPONENT_POOL

        self._game_handler:  GameHandler    | None = None
        self._rl_player:     _RLPlayerProxy | None = None
        self._all_players:   list           | None = None
        self._prev_player                          = None
        self._correct_doubt: bool                  = False
        self._done:          bool                  = False
        self._jokers_in_last_play: bool            = False

    # ── public API ────────────────────────────────────────────────────────────

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)

        n = self._n_players_fixed or random.randint(3, 7)

        self._rl_player = _RLPlayerProxy(1)
        opponents       = [random.choice(self._pool)(i + 2) for i in range(n - 1)]
        self._all_players = [self._rl_player] + opponents
        random.shuffle(self._all_players)
        for i, p in enumerate(self._all_players, 1):
            p.id = i

        initialize(self._all_players, deck_size=14, n_jollies=2)
        self._game_handler  = GameHandler(self._all_players, deck_size=14)
        self._correct_doubt        = False
        self._done                 = False
        self._prev_player          = None
        self._jokers_in_last_play  = False

        self._game_handler.append_event(GameStartEvent(
            player_ids=[p.id for p in self._all_players],
            initial_card_counts={p.id: len(p.cards) for p in self._all_players},
        ))

        obs, _ = self._advance_to_rl_turn()
        return obs, {}

    def step(self, action: int):
        assert not self._done, "call reset() before step()"

        td       = self._rl_player._pending_turn
        is_first = self._game_handler.is_first_hand()
        output   = action_to_output(action, self._rl_player, td, is_first)

        reward, terminated = self._apply_move(output, self._rl_player)
        if terminated:
            self._done = True
            return np.zeros(OBS_DIM, dtype=np.float32), reward, True, False, {}

        obs, done = self._advance_to_rl_turn()
        if done:
            self._done = True
            won = self._rl_player in self._game_handler.get_winners()
            return obs, (1.0 if won else -1.0), True, False, {}

        return obs, 0.0, False, False, {}

    # ── internal helpers ──────────────────────────────────────────────────────

    def _advance_to_rl_turn(self) -> tuple[np.ndarray, bool]:
        """Run opponents' turns until it is the RL agent's turn. Returns (obs, game_over)."""
        gh = self._game_handler

        while gh.n_winners_players() < 1 and gh.turn.counter < MAX_TURNS:
            if not self._correct_doubt:
                self._prev_player, this_player = gh.next_turn()
            else:
                self._correct_doubt = False
                this_player = gh.players.this

            if this_player is self._rl_player:
                td  = generate_player_data(gh)
                self._rl_player._pending_turn = td
                obs = build_obs(td, list(self._rl_player.cards.hand), self._jokers_in_last_play)
                return obs, False

            td     = generate_player_data(gh)
            output = this_player.play(td)
            _, terminated = self._apply_move(output, this_player)
            if terminated:
                break

        return np.zeros(OBS_DIM, dtype=np.float32), True

    def _apply_move(self, output: TurnOutput, this_player) -> tuple[float, bool]:
        """Apply a TurnOutput to the game state. Returns (reward, game_over_for_rl_agent)."""
        gh   = self._game_handler
        prev = self._prev_player

        if output.doubt and gh.is_first_hand():
            is_first  = True
            fake_td   = self._rl_player._pending_turn or generate_player_data(gh)
            output    = action_to_output(1, this_player, fake_td, is_first)

        if output.doubt:
            latest_snap = list(gh.get_latest_played_cards())
            board_snap  = list(gh.get_board())
            declared    = gh.get_current_number()
            jokers_played = gh.jokers_in_latest()
            self._jokers_in_last_play = False

            if jokers_played:
                board = list(gh.get_board())
                for j in jokers_played:
                    board.remove(j)
                this_player.add_cards(board)
                gh.reset_board()
                gh.append_event(DoubtResolvedEvent(
                    doubter_id=this_player.id, target_id=prev.id, correct=False,
                    latest_cards=latest_snap, board_cards=board,
                    declared_number=declared, jokers_discarded=len(jokers_played),
                ))
            elif gh.is_honest():
                this_player.add_cards(gh.get_board())
                gh.reset_board()
                gh.append_event(DoubtResolvedEvent(
                    doubter_id=this_player.id, target_id=prev.id, correct=False,
                    latest_cards=latest_snap, board_cards=board_snap,
                    declared_number=declared,
                ))
            else:
                self._correct_doubt = True
                prev.add_cards(gh.get_board())
                gh.reset_board()
                gh.append_event(DoubtResolvedEvent(
                    doubter_id=this_player.id, target_id=prev.id, correct=True,
                    latest_cards=latest_snap, board_cards=board_snap,
                    declared_number=declared,
                ))

        else:
            if gh.is_first_hand():
                num = output.number or random.choice(gh.board.availables or [1])
                gh.set_current_number(num)
            gh.set_board_cards(output.cards)
            self._jokers_in_last_play = bool(gh.jokers_in_latest())
            gh.append_event(CardsPlayedEvent(
                player_id=this_player.id,
                declared_number=gh.get_current_number(),
                n_cards=len(output.cards),
            ))

        for p in gh.playing_players():
            discarded = p.discard_cards()
            gh.set_discarded_cards(discarded)
            for number in discarded:
                gh.append_event(DiscardEvent(player_id=p.id, card_number=number))

        if prev is not None and prev.has_no_cards():
            gh.set_winners(prev)
            gh.append_event(PlayerWonEvent(player_id=prev.id, position=gh.n_winners_players()))
            if prev is self._rl_player:
                return 1.0, True
            if (self._rl_player not in gh.playing_players() and
                    self._rl_player not in gh.get_winners()):
                return -1.0, True

        if gh.n_winners_players() >= 1 or gh.turn.counter >= MAX_TURNS:
            won = self._rl_player in gh.get_winners()
            return (1.0 if won else -1.0), True

        return 0.0, False
