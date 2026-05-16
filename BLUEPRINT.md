# Dubito — Bot Blueprint

This is a self-contained reference. Read it fully before writing any code. Everything you need to implement a bot is here — you should not need to open any other file.

---

## 1. The Game

### Deck and setup

- Cards are valued **1–13**, with **4 copies of each** value → 52 cards total.
- **2 jokers** (value `0`) are added to the deck → 54 cards total.
- Cards are dealt evenly to all players in a round-robin fashion at the start.
- There are **3–8 players**. The game ends when **2 players remain** — those two players both lose. At least 3 players are required.

### On each turn a player must do one of two things:

**A) Play cards**
- Place **1, 2, or 3 cards** face-down on the board.
- Declare a **number** (1–13). This is the number you claim all your cards are.
- This can be a **truthful play** (your cards actually match the declared number) or a **bluff** (they don't).
- On the **very first turn of a round** (board is empty), the player who goes first gets to pick any number. Doubting is **illegal** when the board is empty.

**B) Doubt the previous player**
- Challenge the previous player's declared play.
- The cards are revealed:
  - If the previous player was **honest** (or played a joker) → the joker (if any) is discarded and the doubter takes **all remaining board cards** into their hand. Bad for the doubter.
  - If the previous player was **bluffing** → the bluffer takes **all board cards** into their hand. Bad for the bluffer. The doubter then gets to play immediately (a free turn).

### Joker special rule

A joker (value `0`) can be played in two valid ways:
- **Joker only** — play just the joker, declaring any number.
- **Joker + matching cards** — play the joker alongside cards that genuinely match the declared number (e.g. joker + two 7s, declaring 7).

In both cases, the joker makes the play count as **honest** if doubted:
- The joker itself is **discarded** (permanently removed from the game).
- All **other** board cards (from this and previous plays in the round) go to the doubter.

So playing a joker protects you from a correct doubt — but the doubter picks up every non-joker card on the board, which can be a large penalty.

### Discarding four-of-a-kind

- At the end of every turn, if any player holds **4 cards of the same value**, those 4 cards are **automatically discarded** (permanently removed from the game).
- This is the primary way to reduce your hand size — and why bluffing smartly to dump cards is important.

### Winning

- A player wins the moment they have **0 cards** in their hand.
- This is checked at the end of each turn, after discards.
- The game ends when **2 players remain** — those two players both lose. This means a minimum of **3 players** is required for the game to produce a winner.
- **Finishing positions:**
  - **Hard win** (1st place) — first player to empty their hand. The best possible outcome and the primary goal.
  - **Soft win** (2nd to n−2 place) — emptied their hand while ≥3 players were still active. Better than losing, but not the target.
  - **Loss** (last 2 players) — the two players still holding cards when the game ends. Both are losers regardless of card count.
- Design your bot to **prioritize the hard win**: play aggressively to empty your hand first rather than sitting back to avoid losing.

### Round structure

- A "round" starts when the board is empty. The first player picks a number and plays cards.
- Subsequent players must either play cards (claiming to play that same number) or doubt the previous player.
- A round ends when someone doubts (board resets) or the pile gets picked up.
- The **streak** counter tracks how many consecutive turns have passed without a doubt — it's a proxy for how many cards are on the board.

---

## 2. Decision Tree

Every bot turn follows this exact structure. The **5 lettered nodes (A–E)** are the only decisions your bot makes. Everything else — legality checks, forced bluffs, hand manipulation — is handled by the framework automatically.

```
MY TURN
│
├─ First hand? (board is empty, board_cards == 0)
│   │
│   ├─ YES ──► Must play cards. Doubting is illegal.
│   │           ├─ [A] bluff_first_hand()    → True = bluff,   False = honest
│   │           └─ [B] maximize_first_hand() → True = maximize, False = random 1–3
│   │
│   └─ NO ───► Regular turn.
│               │
│               ├─ [C] should_doubt() → True = doubt prev player
│               │                       False = play cards
│               │
│               └─ if Play:
│                   ├─ Do I hold the current number in my hand?
│                   │   ├─ YES ──► [D] bluff_regular() → True = bluff anyway
│                   │   │                                False = play honestly
│                   │   └─ NO  ──► Forced bluff. [D] is skipped.
│                   │
│                   └─ [E] maximize_regular() → True = maximize, False = random 1–3
```

### What "honest" and "bluff" mean in practice

| Situation | Honest | Bluff |
|---|---|---|
| First hand | `pick_most()` — plays all cards of the most-common value; declares that value | `pick_random(n)` — plays n random cards; declares a random number from `playing_cards` |
| Regular turn | `pick_all(current_number)` if maximize, else `pick(current_number, k)` for random k | `pick_random(3)` if maximize, else `pick_random(random 1–3)` |

### What "maximize" means

- `maximize=True` → play **as many cards as possible** (up to 3 on first hand, or all matching on regular turns).
- `maximize=False` → play a **random amount** between 1 and 3 (or 1 and available matching cards).

---

## 3. Input — TurnData

Every method receives a single `TurnData` object. By convention it is named `p`.

### Turn state

| Field | Type | Description |
|---|---|---|
| `p.board_cards` | `int` | Total cards currently on the board. `0` means the board is empty (first hand). |
| `p.playing_cards` | `list[int]` | Card values still in circulation (not yet discarded as four-of-a-kind). Shrinks as the game progresses. |
| `p.current_number` | `int` | The number declared by the previous player. `0` if it is the first hand. |
| `p.n_cards_played` | `int` | How many cards the previous player placed this turn (1, 2, or 3). |
| `p.streak` | `int` | Consecutive turns without a doubt. Resets to 0 after every doubt. Higher = larger board pile. |
| `p.n_players` | `int` | Number of players currently still active in the game. |

### Yourself

| Field | Type | Description |
|---|---|---|
| `p.my_n_cards` | `int` | Your current card count. |
| `p.me` | `PlayerData` | Your own historical stats (see PlayerData fields below). |

### Neighbours

`p.prev` is the player who played just before you (the one you can doubt).
`p.next` is the player who will play after you (the one who can doubt you).

Both are `PlayerData` objects with these fields:

| Field | Type | Description |
|---|---|---|
| `.n_cards` | `int` | Their current card count. If `p.prev.n_cards == 0`, they are about to win unless doubted. |
| `.turns` | `int` | Total turns they have played in this game. |
| `.not_first_turns` | `int` | Turns played on a non-opening hand. Use this as the denominator for doubt rate. |
| `.doubts` | `int` | Total times they have doubted. `doubts / not_first_turns` = their doubt rate. |
| `.honest_times` | `int` | Times they were caught being honest when doubted. |
| `.dishonest_times` | `int` | Times they were caught bluffing when doubted. |

> **Note on stats**: `honest_times` and `dishonest_times` only accumulate when a player gets *doubted*. A player who never gets doubted will have zeros in both — this does not mean they are honest. Use the ratio `dishonest / (honest + dishonest)` and treat a zero denominator as uncertainty (e.g. assume 0.5).

---

## 4. Methods available on `self`

These are inherited from the framework. You can call them freely inside your A–E methods.

### Hand inspection (read-only — safe to call anywhere)

| Call | Returns | Description |
|---|---|---|
| `self.cards.count(n)` | `int` | How many cards of value `n` you currently hold. |
| `self.cards.count_all()` | `Counter` | A `Counter` of all values in your hand. E.g. `{7: 3, 2: 1, 11: 2}`. |
| `self.cards.has(n)` | `bool` | True if you hold at least one card of value `n`. |
| `self.cards.all_equal()` | `bool` | True if every card in your hand has the same value. |
| `len(self.cards)` | `int` | Total number of cards in your hand (same as `p.my_n_cards`). |

### State helpers (read-only — safe to call anywhere)

| Call | Returns | Description |
|---|---|---|
| `self.can_play_truthfully(p)` | `bool` | True if your hand contains `p.current_number`. Tells you whether honest play is an option. |
| `self.prev_player_started_turn(p)` | `bool` | True if `prev` was the one who opened this round (i.e. `n_cards_played == board_cards`). Means prev chose the current number themselves — slightly more likely to be honest. |

### ⚠ Do NOT call these directly

The following methods exist on the base class but are called **automatically by the framework** based on your A–E answers. Do not call them yourself inside A–E methods:

`self.bluff(...)`, `self.play_truthfully(...)`, `self.doubt(...)` — these assemble the final move and modify your hand. The framework calls them after it collects your boolean answers.

---

## 5. Output — what your methods must return

Each of the 5 methods must return exactly a `bool`. Nothing else. The framework assembles the final game action from your answers.

| Method | `True` means | `False` means |
|---|---|---|
| `bluff_first_hand` | Play random cards, declare a random number | Play your strongest suit honestly |
| `maximize_first_hand` | Play as many cards as possible | Play a random amount (1–3) |
| `should_doubt` | Challenge the previous player's move | Play cards yourself |
| `bluff_regular` | Play random cards (ignoring the current number) | Play cards matching the current number |
| `maximize_regular` | Maximize cards played | Play a random amount |

---

## 6. Game Events

After every game action the engine calls `observe(event)` on **every active player**, not just the one whose turn it is. By default this is a no-op. Override it to maintain an internal belief state about what cards opponents hold.

This is the only way to learn information that `TurnData` alone cannot give you — such as which specific cards a player picked up after a doubt, or that a player definitely no longer holds a certain number after discarding.

### Event types

All event classes are importable from `dubito.game_data`.

---

#### `CardsPlayedEvent` — someone placed cards on the board

| Field | Type | Description |
|---|---|---|
| `player_id` | `int` | Who played. |
| `declared_number` | `int` | The number they claimed. |
| `n_cards` | `int` | How many cards placed face-down. |

> The actual card values are **not included** — they are hidden until a doubt reveals them. This event is probabilistic only.

---

#### `DoubtResolvedEvent` — a doubt was called and resolved

| Field | Type | Description |
|---|---|---|
| `doubter_id` | `int` | Who doubted. |
| `target_id` | `int` | Who was doubted (the last player to place cards). |
| `correct` | `bool` | `True` = bluffer caught (target picks up cards). `False` = doubter wrong (doubter picks up cards). |
| `latest_cards` | `list[int]` | The actual cards in the last play — now revealed. |
| `board_cards` | `list[int]` | Every card the loser picks up (full board contents). |
| `declared_number` | `int` | The number that was declared. |
| `jokers_discarded` | `int` | Number of jokers discarded (joker protection case). `0` in normal doubts. |
| `.loser_id` | `int` (property) | Convenience: `target_id` if `correct`, else `doubter_id`. |

> This is the **highest-information event**. When `correct=False` (you doubted and were wrong) you learn both that the target was honest *and* exactly which cards went into your hand. When `correct=True` you learn what the bluffer actually played.

---

#### `DiscardEvent` — a player discarded a four-of-a-kind

| Field | Type | Description |
|---|---|---|
| `player_id` | `int` | Who discarded. |
| `card_number` | `int` | The value of the 4 cards removed. |

> **Certain knowledge**: after this event, `player_id` holds zero cards of `card_number`. No probability involved.

---

#### `PlayerWonEvent` — a player left the game

| Field | Type | Description |
|---|---|---|
| `player_id` | `int` | Who finished. |
| `position` | `int` | Their finishing position (`1` = first place, `2` = second, …). |

---

### Using observe()

```python
from dubito.game_data import (
    TurnData,
    CardsPlayedEvent, DoubtResolvedEvent, DiscardEvent, PlayerWonEvent,
)

def observe(self, event) -> None:
    match event:
        case DoubtResolvedEvent(correct=True) as e:
            # Bluffer caught: we know exactly what the bluffer played
            # and that they now hold all of board_cards
            self.mark_bluff(e.target_id, e.latest_cards, e.declared_number)
            self.add_known_cards(e.target_id, e.board_cards)

        case DoubtResolvedEvent(correct=False) as e:
            # Doubter wrong: target was honest, doubter picks up board
            # We know the honest cards target played, and exactly what went
            # into the doubter's hand
            self.mark_honest(e.target_id, e.latest_cards, e.declared_number)
            self.add_known_cards(e.loser_id, e.board_cards)

        case DiscardEvent() as e:
            # Certain: this player no longer holds this number at all
            self.mark_exhausted(e.player_id, e.card_number)

        case CardsPlayedEvent() as e:
            # Probabilistic only — update bluff likelihood estimate
            self.update_prior(e.player_id, e.declared_number, e.n_cards)

        case PlayerWonEvent():
            pass  # player gone — clean up their belief entry if needed
```

---

## 7. Template

Copy this exactly. Rename `MyBot`. Put it in `bots/manual/` (hand-crafted) or `bots/llms/` (LLM-based). Implement the 5 methods.

```python
from bots.base import BotBase
from dubito.game_data import TurnData


class MyBot(BotBase):

    def bluff_first_hand(self, p: TurnData) -> bool:
        ...

    def maximize_first_hand(self, p: TurnData) -> bool:
        ...

    def should_doubt(self, p: TurnData) -> bool:
        ...

    def bluff_regular(self, p: TurnData) -> bool:
        ...

    def maximize_regular(self, p: TurnData) -> bool:
        ...
```

### If your bot needs internal state between turns

Add `__init__` and call `super().__init__(id)`:

```python
def __init__(self, id: int) -> None:
    super().__init__(id)
    self.suspicion: dict[int, float] = {}   # example: track suspicion per player id
```

### If you need to update state before making decisions (without events)

Override `play()` and call `super().play(p)` at the end:

```python
def play(self, p: TurnData):
    self._update(p)        # update your state first
    return super().play(p) # framework calls A–E as usual

def _update(self, p: TurnData) -> None:
    ...
```

### If you want to track game events across all players' turns

Override `observe()`. It is called automatically for every player after every game action — whether or not it is your turn.

```python
def observe(self, event) -> None:
    from dubito.game_data import DoubtResolvedEvent, DiscardEvent
    match event:
        case DoubtResolvedEvent() as e:
            # e.correct, e.target_id, e.latest_cards, e.board_cards …
            ...
        case DiscardEvent() as e:
            # certain: e.player_id no longer holds e.card_number
            ...
```

---

## 8. Worked example — a complete minimal bot

```python
from bots.base import BotBase
from dubito.game_data import TurnData


class ExampleBot(BotBase):
    """
    - First hand: always honest, maximize.
    - Doubt if prev is about to win OR played 3 cards.
    - Never voluntarily bluffs.
    - Always maximizes.
    """

    def bluff_first_hand(self, p: TurnData) -> bool:
        return False   # pick our strongest number honestly

    def maximize_first_hand(self, p: TurnData) -> bool:
        return True    # dump as many cards as possible

    def should_doubt(self, p: TurnData) -> bool:
        if p.prev.n_cards == 0:
            return True              # they're about to win — must stop them
        return p.n_cards_played == 3  # 3 cards played is suspicious

    def bluff_regular(self, p: TurnData) -> bool:
        return False   # honest whenever possible

    def maximize_regular(self, p: TurnData) -> bool:
        return True
```

---

## 9. Key signals and strategic hints

### From TurnData (available every turn)

| Signal | How to compute | What it tells you |
|---|---|---|
| Prev's bluff rate | `p.prev.dishonest_times / (p.prev.honest_times + p.prev.dishonest_times)` | How likely prev is bluffing right now. Treat 0-denominator as 0.5 (unknown). |
| Next's doubt rate | `p.next.doubts / p.next.not_first_turns` | How likely next will doubt you. Treat 0-denominator as 0.5. |
| Cards I have of current number | `self.cards.count(p.current_number)` | If 0: you must bluff. If ≥ 3: honest play removes as many cards as bluffing. |
| Prev about to win | `p.prev.n_cards == 0` | They win unless doubted. Always doubt here. |
| Prev chose the number | `self.prev_player_started_turn(p)` | They picked the current number → slightly more likely to hold it. |
| Board pile size | `p.board_cards` or `p.streak` | Doubting costs you all these cards if wrong. High streak = big risk. |
| My card count | `p.my_n_cards` | Low (≤4) → close to winning, play safe. High (≥18) → desperate, take risks. |

### From observe() (accumulated across the whole game)

| Event | What you can learn |
|---|---|
| `DoubtResolvedEvent(correct=True)` | Bluffer's actual cards + exactly which cards they now hold (board pickup). |
| `DoubtResolvedEvent(correct=False)` | Target was honest + exactly which cards went into the doubter's hand. |
| `DiscardEvent` | Player definitively holds zero of that number — certain, no inference needed. |
| `CardsPlayedEvent` | Probabilistic update: N cards declared as X makes holding X more or less likely depending on what you know. |

> **observe() vs TurnData**: `TurnData` gives you a per-turn snapshot with aggregate stats. `observe()` gives you raw events with exact card information. Use both — `TurnData` for fast rule-based decisions, `observe()` for building a richer belief model when the extra complexity pays off.

**Bluff vs honest on a regular turn** — a useful comparison:

| Situation | Honest play removes | Bluff removes |
|---|---|---|
| I have 1 matching card | 1 card | 3 cards (if maximize) |
| I have 2 matching cards | 2 cards | 3 cards (if maximize) |
| I have 3+ matching cards | 3+ cards | 3 cards (if maximize) |

→ Bluffing is only worth the risk when you have **fewer than 3 matching cards** and next player is unlikely to doubt you.

**Hard win vs soft win** — a `PlayerWonEvent` with `position > 1` is a soft win for that player. You can use this to track how many opponents are left and recalibrate your aggression:

| Situation | Recommended stance |
|---|---|
| Many players remain, you have many cards | Aggressive — bluff and maximize to shed cards fast |
| Few players remain, you have few cards | Careful — a wrong doubt could cost you the hard win |
| `p.prev.n_cards == 0` | Always doubt — letting them win costs you your position |

> Hard wins score better than soft wins in the experiment runner. A bot that consistently gets soft wins but rarely finishes first is underperforming.

---

## 10. Constraints

- Each of the 5 methods must return **only** `True` or `False`. No other return type.
- Do **not** call `self.bluff()`, `self.play_truthfully()`, or `self.doubt()` inside your methods — the framework calls those for you.
- Do **not** modify `self.cards` directly.
- Do **not** import from `dubito.core_game`, `dubito.handlers`, or `dubito.hand`.
- The imports you need:
  ```python
  from bots.base import BotBase
  from dubito.game_data import TurnData

  # Optional — only if using observe():
  from dubito.game_data import CardsPlayedEvent, DoubtResolvedEvent, DiscardEvent, PlayerWonEvent
  ```
- Bot files live in `bots/manual/` (hand-crafted) or `bots/llms/` (LLM-based).
- Your class name must match the filename (e.g. `class GeminiBot` in `bots/llms/gemini.py`).
