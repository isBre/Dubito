"""
ClaudeFableBot — an information-maximal, expected-value bot authored by Claude Fable.

Unlike the A–E template bots, this bot overrides play_first_turn / play_regular_turn
directly: it needs full control over which cards are played (joker tactics, bluff
sizing, opener declarations), which the boolean hooks cannot express.

It is built on five pillars:

1. **Exact card tracking.** Every pile pickup is public (DoubtResolvedEvent.board_cards),
   every discard is public, and the bot knows its own pile contributions. From these it
   maintains, per opponent, a sound lower bound of cards they certainly hold, plus the
   global pool of cards whose location is unknown.

2. **Bayesian opponent model.** Per-opponent bluff and doubt propensities are tracked as
   Beta-smoothed rates, so one observation does not swing the estimate the way the raw
   ratios used by other bots do. Doubt resolutions that follow a player's winning dump
   are misattributed by the engine to an innocent player — those are filtered out.

3. **Claim feasibility.** When the previous player claims "n cards of X", a hypergeometric
   model over the unseen pool gives P(they could even hold that), jokers included. The
   bluff prior is fused with this likelihood via Bayes; impossible claims are certainties.

4. **Expected value, in card units.** Doubting and every candidate play (honest max,
   honest + joker, joker alone, bluff of 1–3 trash cards) are scored by expected cards
   shed/eaten, weighted by hand-size urgency, threat level of the previous player, and
   the dilution of damage among rivals. The best action wins.

5. **Engine-exact endgame.** A hand-emptying play wins immediately and can never be
   doubted, so a hand of ≤3 cards is a guaranteed win on the bot's next turn. The bot
   dumps unconditionally at ≤3, values reaching ≤3 via un-doubtable (honest/joker) plays,
   and doubts aggressively when the previous player is about to reach that state.
"""

import math
from collections import Counter

from bots.base import BotBase
from dubito.game_data import (
    TurnData, TurnOutput,
    GameStartEvent, CardsPlayedEvent, DoubtResolvedEvent, DiscardEvent, PlayerWonEvent,
)


# ── Tunable constants ──────────────────────────────────────────────────────────

# Beta priors (pseudo-observations). Field averages: ~45% of doubted plays are
# bluffs, ~30% of doubt opportunities are taken.
BLUFF_PRIOR = (1.0, 1.2)        # (caught, verified-honest)
DOUBT_PRIOR = (1.0, 2.3)        # (doubts, declined opportunities)

# Context multipliers on the bluff prior (odds space).
BLUFF_K_MULT = {1: 0.85, 2: 1.15, 3: 1.45}   # more cards claimed → more suspicious
BLUFF_OPENER_MULT = 0.70                      # opener picked their own number
WINNER_DUMP_BLUFF = 0.80                      # prior that a winning dump was a bluff

# How much the next player's doubt rate reacts to my play size.
DOUBT_K_REACT = {1: 0.85, 2: 1.10, 3: 1.45}

# EV weights (rough "card units").
REPLAY_BONUS = 1.9        # correct doubt → free opener (tempo + a safe dump)
TEMPO_LOSS = 0.4          # wrong doubt → the player after me opens fresh
REPLAY_GIFT = 0.8         # my caught bluff hands the next player a free opener
REPUTATION_COST = 0.25    # each caught bluff makes adaptive opponents doubt me more
JOKER_SPEND_COST = 0.7    # a joker kept is insurance for a forced-bluff emergency
REACH3_BONUS = 2.8        # play leaves me at ≤3 cards → guaranteed win next turn
REACH3_CONTESTED = 1.6    # ...but a rival is also at ≤3 and acts before me
REACH4_BONUS = 0.6


def _beta_rate(hits: int, misses: int, prior: tuple[float, float]) -> float:
    a, b = prior
    return (hits + a) / (hits + misses + a + b)


def _hyper_at_least(pop: int, succ: int, draws: int, needed: int) -> float:
    """P(at least `needed` successes when drawing `draws` from `pop` with `succ` successes)."""
    if needed <= 0:
        return 1.0
    succ = max(0, min(succ, pop))
    draws = max(0, min(draws, pop))
    if needed > min(succ, draws):
        return 0.0
    total = math.comb(pop, draws)
    if total == 0:
        return 0.0
    miss = sum(
        math.comb(succ, x) * math.comb(pop - succ, draws - x)
        for x in range(0, needed)
        if draws - x <= pop - succ
    )
    return 1.0 - miss / total


class ClaudeFableBot(BotBase):

    def __init__(self, id: int) -> None:
        super().__init__(id)
        self._reset_tracking()

    def reset(self) -> None:
        super().reset()
        self._reset_tracking()

    def _reset_tracking(self) -> None:
        self._idx = 0                  # history events already ingested
        self._bluff: dict[int, list[int]] = {}   # pid → [caught, verified honest]
        self._doubtc: dict[int, list[int]] = {}  # pid → [doubts, declined opportunities]
        self._known: dict[int, Counter] = {}     # pid → cards they certainly hold
        self._gone = Counter()         # card number → copies permanently discarded
        self._my_pile = Counter()      # my own cards currently sitting in the pile
        self._pile = 0                 # reconstructed board size
        self._last_play = None         # most recent CardsPlayedEvent
        self._my_caught = 0            # times I was caught bluffing this game

    # ── History ingestion (incremental — each event processed once) ───────────

    def _ingest(self, history: list) -> None:
        if self._idx > len(history):   # new game, instance reused without reset
            self._reset_tracking()
        for e in history[self._idx:]:
            if isinstance(e, GameStartEvent):
                self._reset_tracking()
                self._idx = 0
            elif isinstance(e, CardsPlayedEvent):
                if self._pile > 0 and e.player_id != self.id:
                    self._doubtc.setdefault(e.player_id, [0, 0])[1] += 1
                self._pile += e.n_cards
                self._last_play = e
                if e.player_id != self.id:
                    # They played n face-down cards: any certainty about their hand
                    # decays by n per number (the played cards may have been those).
                    k = self._known.get(e.player_id)
                    if k:
                        for num in list(k):
                            k[num] -= e.n_cards
                            if k[num] <= 0:
                                del k[num]
            elif isinstance(e, DoubtResolvedEvent):
                d = self._doubtc.setdefault(e.doubter_id, [0, 0])
                d[0] += 1
                # After a winning dump the engine attributes the doubt to an innocent
                # player — only count honesty stats when the target really played last.
                if self._last_play is not None and self._last_play.player_id == e.target_id:
                    b = self._bluff.setdefault(e.target_id, [0, 0])
                    b[0 if e.correct else 1] += 1
                    if e.correct and e.target_id == self.id:
                        self._my_caught += 1
                loser = e.target_id if e.correct else e.doubter_id
                if loser != self.id:
                    self._known.setdefault(loser, Counter()).update(e.board_cards)
                self._gone[0] += e.jokers_discarded
                self._my_pile.clear()
                self._pile = 0
                self._last_play = None
            elif isinstance(e, DiscardEvent):
                self._gone[e.card_number] = 4
                for k in self._known.values():
                    k.pop(e.card_number, None)
            elif isinstance(e, PlayerWonEvent):
                # Keep their known cards: a winning dump may still be (windfall-)doubted.
                pass
        self._idx = len(history)

    # ── Opponent model ─────────────────────────────────────────────────────────

    def _bluff_rate(self, pid: int) -> float:
        caught, honest = self._bluff.get(pid, (0, 0))
        return _beta_rate(caught, honest, BLUFF_PRIOR)

    def _doubt_rate(self, pid: int) -> float:
        doubts, declined = self._doubtc.get(pid, (0, 0))
        return _beta_rate(doubts, declined, DOUBT_PRIOR)

    def _claim_feasibility(self, p: TurnData, target_id: int, target_hand_now: int,
                           number: int, n_claimed: int) -> float:
        """P(target could hold/play `n_claimed` cards matching `number`), jokers included."""
        my = self.cards.count_all()
        known_target = self._known.get(target_id, Counter())

        def located(num: int) -> int:
            return (my[num] + self._my_pile[num]
                    + sum(k[num] for k in self._known.values()))

        circulating = lambda num: (2 if num == 0 else 4) - self._gone[num]
        # Successes: matching cards (number or joker) that could be anywhere unseen.
        succ = max(0, circulating(number) - located(number)) \
             + max(0, circulating(0) - located(0))
        # Population: all cards whose location I don't know, excluding the face-down
        # pile (on the table, certainly not in target's hand). Not subtracting unknown
        # pile cards from `succ` keeps the estimate conservative.
        total_circ = sum(circulating(num) for num in range(0, 14) if circulating(num) > 0)
        located_all = len(self.cards) + sum(self._my_pile.values()) \
                    + sum(sum(k.values()) for k in self._known.values())
        pile_unknown = max(0, p.board_cards - sum(self._my_pile.values()))
        pop = max(0, total_circ - located_all - pile_unknown)

        known_match = known_target[number] + known_target[0]
        needed = n_claimed - known_match
        # Unknown slots of their hand at play time (they had hand_now + n_claimed cards).
        draws = max(0, target_hand_now + n_claimed - sum(known_target.values()))
        return _hyper_at_least(pop, succ, draws, needed)

    def _p_bluff(self, p: TurnData) -> float:
        """P(the play on the table is a bluff), Bayes-fusing prior tendency and feasibility."""
        play = self._last_play
        attributed = play is not None and play.player_id == p.prev_player_id
        if attributed:
            prior = self._bluff_rate(p.prev_player_id) * BLUFF_K_MULT.get(p.n_cards_played, 1.0)
            if p.n_cards_played == p.board_cards:      # they opened and chose the number
                prior *= BLUFF_OPENER_MULT
            hand_now = p.player_card_counts.get(p.prev_player_id, 1)
            target = p.prev_player_id
        else:
            # The last play was a winning dump (its player already left the game). The
            # engine resolves a doubt here against those cards, but charges an innocent
            # player — for us, only P(that dump was a bluff) matters.
            prior = WINNER_DUMP_BLUFF
            hand_now = 0
            target = play.player_id if play is not None else p.prev_player_id
        prior = min(max(prior, 0.02), 0.98)
        feasible = self._claim_feasibility(
            p, target, hand_now, p.current_number,
            p.n_cards_played if play is None else play.n_cards,
        )
        post = prior / (prior + (1.0 - prior) * feasible)
        return min(max(post, 0.01), 0.999)

    # ── EV weights ─────────────────────────────────────────────────────────────

    def _me_eat_factor(self) -> float:
        n = len(self.cards)
        if n <= 5:
            return 1.7      # near the win — picking up a pile is devastating
        if n <= 8:
            return 1.25
        if n >= 15:
            return 0.75     # already buried — marginal cards matter less
        return 1.0

    def _threat_mult(self, count: int) -> float:
        if count <= 3:
            return 3.0      # they dump-win on their next turn unless stopped now
        if count <= 5:
            return 1.8
        if count <= 8:
            return 1.2
        return 1.0

    def _reach_bonus(self, p: TurnData, n_after: int) -> float:
        if n_after <= 3:
            rivals_close = any(
                c <= 3 for pid, c in p.player_card_counts.items() if pid != self.id
            )
            return REACH3_CONTESTED if rivals_close else REACH3_BONUS
        if n_after == 4:
            return REACH4_BONUS
        return 0.0

    def _doubt_ev(self, p: TurnData) -> float:
        p_b = self._p_bluff(p)
        pile = p.board_cards
        opp_relief = 1.0 / max(2, p.n_players - 1)
        prev_count = p.player_card_counts.get(p.prev_player_id, 8)
        gain = pile * opp_relief * self._threat_mult(prev_count) + REPLAY_BONUS
        loss = pile * self._me_eat_factor() + TEMPO_LOSS
        return p_b * gain - (1.0 - p_b) * loss

    # ── Play candidates ────────────────────────────────────────────────────────

    def _trash_indexes(self, amount: int, protect: int) -> list[int]:
        """Indexes of the `amount` least useful cards: never jokers, never `protect`,
        singletons of mostly-dead numbers first, sets broken only as a last resort."""
        hand = self.cards.hand
        counts = self.cards.count_all()

        def usefulness(i: int) -> tuple:
            num = hand[i]
            if num == 0:
                return (3, 0, 0)                      # jokers last
            if num == protect:
                return (2, counts[num], 0)            # current number: keep if possible
            unseen = 4 - self._gone[num] - counts[num]
            return (1, counts[num], unseen)           # dead singletons first

        order = sorted(range(len(hand)), key=usefulness)
        return order[:amount]

    def _play_ev(self, p: TurnData, k: int, honest_proof: bool, spends_joker: bool) -> float:
        n_after = len(self.cards) - k
        opp_relief = 1.0 / max(2, p.n_players - 1)
        d_base = self._doubt_rate(p.next_player_id)
        if honest_proof:
            ev = k + self._reach_bonus(p, n_after)
            ev += d_base * (p.board_cards + k) * opp_relief * 0.6   # their wrong doubt feeds them
            if spends_joker and n_after > 3:
                ev -= JOKER_SPEND_COST
            return ev
        my_rep = self._my_caught * 0.07
        d_k = min(0.97, max(0.02, d_base * DOUBT_K_REACT.get(k, 1.0) + my_rep))
        win_part = k + self._reach_bonus(p, n_after)
        lose_part = (p.board_cards + k) * self._me_eat_factor() + REPLAY_GIFT + REPUTATION_COST
        return (1.0 - d_k) * win_part - d_k * lose_part

    def _emit(self, p: TurnData, cards: list[int], number: int | None) -> TurnOutput:
        self._my_pile.update(cards)
        return TurnOutput(doubt=False, number=number, cards=cards)

    def _dump_all(self, p: TurnData, first_turn: bool) -> TurnOutput:
        """Hand-emptying play: an immediate, un-doubtable win."""
        cards = self.cards.pick_idx(list(range(len(self.cards.hand))))
        number = None
        if first_turn:
            real = [c for c in cards if c != 0]
            number = Counter(real).most_common(1)[0][0] if real else p.playing_cards[0]
        return TurnOutput(doubt=False, number=number, cards=cards)

    # ── Turn entry points (override the framework for full card control) ──────

    def play_first_turn(self, p: TurnData) -> TurnOutput:
        self._ingest(p.history)
        if len(self.cards) <= 3:
            return self._dump_all(p, first_turn=True)

        counts = self.cards.count_all()
        candidates = [(num, c) for num, c in counts.items() if num != 0]
        # Best honest opener: dump the most copies; tie-break toward numbers with the
        # fewest copies left unseen (cornering — others must bluff into my doubts).
        def opener_key(item):
            num, c = item
            unseen = 4 - self._gone[num] - c
            return (min(3, c), -unseen)
        best, c = max(candidates, key=opener_key)
        k_honest = min(3, c)

        use_joker = (counts[0] > 0 and k_honest < 3
                     and (len(self.cards) - k_honest - 1 <= 3 or len(self.cards) >= 10))
        ev_honest = self._play_ev(p, k_honest + (1 if use_joker else 0),
                                  honest_proof=True, spends_joker=use_joker)

        # Bluff opener: with an empty pile a caught bluff costs only my own cards back.
        k_bluff = min(3, len(self.cards) - 1)
        ev_bluff = self._play_ev(p, k_bluff, honest_proof=False, spends_joker=False) \
            if k_honest < k_bluff else -1e9

        if ev_bluff > ev_honest:
            idx = self._trash_indexes(k_bluff, protect=best)
            return self._emit(p, self.cards.pick_idx(idx), number=best)
        cards = self.cards.pick(best, k_honest)
        if use_joker:
            cards += self.cards.pick(0, 1)
        return self._emit(p, cards, number=best)

    def play_regular_turn(self, p: TurnData) -> TurnOutput:
        self._ingest(p.history)
        if len(self.cards) <= 3:
            return self._dump_all(p, first_turn=False)

        best_ev, best_action = self._doubt_ev(p), ('doubt', 0, False)

        c = self.cards.count(p.current_number)
        n_jokers = self.cards.count(0)
        if c > 0:
            k = min(3, c)
            ev = self._play_ev(p, k, honest_proof=True, spends_joker=False)
            if ev > best_ev:
                best_ev, best_action = ev, ('honest', k, False)
            if n_jokers > 0 and k < 3:
                ev = self._play_ev(p, k + 1, honest_proof=True, spends_joker=True)
                if ev > best_ev:
                    best_ev, best_action = ev, ('honest', k, True)
        if n_jokers > 0:
            ev = self._play_ev(p, 1, honest_proof=True, spends_joker=True)
            if ev > best_ev:
                best_ev, best_action = ev, ('joker', 1, True)
        n_trash = len(self.cards) - n_jokers - c
        for k in (1, 2, 3):
            if k <= n_trash and k < len(self.cards):
                ev = self._play_ev(p, k, honest_proof=False, spends_joker=False)
                if ev > best_ev:
                    best_ev, best_action = ev, ('bluff', k, False)

        kind, k, joker = best_action
        if kind == 'doubt':
            return TurnOutput(doubt=True, number=None, cards=None)
        if kind == 'honest':
            cards = self.cards.pick(p.current_number, k)
            if joker:
                cards += self.cards.pick(0, 1)
            return self._emit(p, cards, None)
        if kind == 'joker':
            return self._emit(p, self.cards.pick(0, 1), None)
        idx = self._trash_indexes(k, protect=p.current_number)
        return self._emit(p, self.cards.pick_idx(idx), None)

    # ── A–E hooks (required by BotBase; superseded by the overrides above) ────

    def bluff_first_hand(self, p: TurnData) -> bool:
        return False

    def maximize_first_hand(self, p: TurnData) -> bool:
        return True

    def should_doubt(self, p: TurnData) -> bool:
        self._ingest(p.history)
        return self._doubt_ev(p) > 0

    def bluff_regular(self, p: TurnData) -> bool:
        return False

    def maximize_regular(self, p: TurnData) -> bool:
        return True
