# Introduction

The objective of this project was to determine the **most proficient AI for playing Dubito**. Within this endeavor, you'll discover both the game itself and the framework for conducting numerous experiments involving various AI players.

# The Game
**Dubito** is a dynamic card game designed for 3-8 players. To kick off the game, cards are distributed in a round-robin fashion, starting with the initiating player. 

Each turn, players have the option to either make a play or doubt the previous player's move. If there are no cards on the table, players are limited to making a play. When making a play, a player can choose to place 1-3 cards face down and declare a number (ranging from 1 to King). A truthful play occurs when the declared number matches the cards placed (e.g., declaring "1" and placing two cards of value 1), while any other declaration constitutes a bluff.

Alternatively, players can opt to doubt the previous player's claim. If the previous player was indeed bluffing, they collect all cards on the table, and the doubting player proceeds with their turn. Conversely, if the previous player was truthful, the doubting player collects all cards on the table, and the game continues with the next player.

The game culminates when only two players remain, resulting in the elimination of those two players and victory for the remaining participants.

# Simplifications

To reduce the complexity of the experiments, certain simplifications were implemented:

- **Number of winner**: Limited to a single winner, as scenarios with multiple winners in a single game are treated as recursive instances of the "One winner case".
- **Jokers**: 2 jokers (value `0`) are included. A joker acts as any card; if doubted while a joker was played, the joker is discarded and the remaining board cards go to the doubter. Jokers already accumulated in the board pile are kept by whoever picks it up.

# AI

## Decision Tree

Every bot turn follows this exact structure. The lettered nodes **(A–E)** are the only points where strategy matters — everything else is forced by the rules.

```
MY TURN
│
├─ First hand? (board_cards == 0)
│   │
│   ├─ YES ──► Must play cards (doubting is illegal)
│   │           ├─ [A] Bluff or Honest?
│   │           │       BLUFF  → pick any cards, declare a random number
│   │           │       HONEST → pick cards from hand, declare their value
│   │           └─ [B] How many cards to play? (1, 2, or 3)
│   │
│   └─ NO ───► Regular turn
│               │
│               ├─ [C] Doubt or Play?
│               │
│               ├─ if Doubt ──► challenge prev player's last move
│               │
│               └─ if Play
│                   ├─ Can play truthfully?  (do I hold the current number?)
│                   │   ├─ YES ──► [D] Bluff or Honest?
│                   │   │               BLUFF  → pick any cards
│                   │   │               HONEST → pick matching cards
│                   │   └─ NO  ──► forced to Bluff (pick any cards)
│                   │
│                   └─ [E] How many cards to play? (1, 2, or 3)
```

Every bot is a specific strategy for answering **A–E**. The available signals to inform those answers are:

| Signal | Informs | What it tells you |
|---|---|---|
| `dishonest_times(prev_id, history)` / `honest_times(prev_id, history)` | C | Prev player's historical honesty ratio when doubted |
| `n_cards_played` | C | Cards prev just played (1–3); more cards = more suspicious |
| `player_card_counts[prev_player_id]` | C | Prev's remaining cards; 0 means they're about to win → doubt |
| `prev_player_started_turn` | C | Prev set the number this round (they went first) |
| `streak` | C, E | Turns without a doubt; longer = larger pile on the board |
| `doubts_count(next_id, history)` / `turns_count(next_id, history)` | A, D, E | How aggressively the next player doubts; affects how safe you need to be |
| `player_card_counts[next_player_id]` | C, E | Next player's remaining cards |
| `history` (DoubtResolvedEvent.latest_cards) | all | Actual cards revealed in past doubt resolutions — which numbers each player was holding |
| Own hand (`my_cards`) | A, B, D, E | Which numbers you hold and how many of each |

## Input

At each turn the bot receives a `TurnData` dataclass. It has two parts: a **certain snapshot** of the current game state, and a **raw history** of all events from which anything uncertain must be derived.

**Certain snapshot** — engine-verified facts

| Field | Type | Description |
|---|---|---|
| `my_cards` | `list[int]` | Your current hand (private) |
| `current_number` | `int` | Number declared by the previous player (0 on first hand) |
| `board_cards` | `int` | Total cards on the board |
| `n_cards_played` | `int` | How many cards the previous player placed |
| `playing_cards` | `list[int]` | Card numbers still in circulation (not globally discarded) |
| `n_players` | `int` | Number of players still active |
| `player_card_counts` | `dict[int, int]` | Exact card count per player id |
| `streak` | `int` | Consecutive turns without a doubt |
| `my_player_id` | `int` | Your player id |
| `prev_player_id` | `int` | Id of the player before you |
| `next_player_id` | `int` | Id of the player after you |

**History** — raw event log for inference

| Field | Type | Description |
|---|---|---|
| `history` | `list[GameEvent]` | All events since game start, in order |

The event types are:

| Event | Key fields | What it reveals |
|---|---|---|
| `GameStartEvent` | `player_ids`, `initial_card_counts` | Starting configuration |
| `CardsPlayedEvent` | `player_id`, `declared_number`, `n_cards` | Who played, what they claimed, how many cards |
| `DoubtResolvedEvent` | `doubter_id`, `target_id`, `correct`, `latest_cards`, `declared_number` | The actual cards that were face-down — revealed on doubt |
| `DiscardEvent` | `player_id`, `card_number` | Which number was discarded (4-of-a-kind removed) |
| `PlayerWonEvent` | `player_id`, `position` | Who finished and in what place |

`game_data.py` exports four helper functions for the most common history queries:

```python
from dubito.game_data import honest_times, dishonest_times, doubts_count, turns_count

honest_times(player_id, history)    # times player was doubted and found honest
dishonest_times(player_id, history) # times player was caught bluffing
doubts_count(player_id, history)    # times player chose to doubt
turns_count(player_id, history)     # total turns taken (plays + doubts)
```


## Output

Each bot returns a `TurnOutput` dataclass:

| Field | Type | Description |
|---|---|---|
| `doubt` | `bool` | `True` to challenge the previous player, `False` to play cards |
| `number` | `Optional[int]` | Declared number — only set when opening a new round (first hand) |
| `cards` | `Optional[List[int]]` | Cards placed face-down — `None` when doubting |

# Personalized AI

The aim of this project is to attempt to create AIs that achieve better results than other bots. Let's see how to accomplish this.

## Create your AI

Create a class that extends `BotBase` (`bots/base.py`) and implement the five A–E hooks of the decision tree above. Drop the file in `bots/manual/` (or `bots/llms/` for LLM-authored strategies) and import it in that package's `__init__.py` — bots register themselves automatically.

Bots that need full control over *which* cards are played (joker tactics, custom bluff sizes, opener declarations) can override `play_first_turn` / `play_regular_turn` directly instead — see `bots/llms/claude_fable.py`.

## Test your AI

Run `python -m experiments`. The bot pool, number of games, and output paths are configured in `experiment.yaml` (every registered bot plays when no explicit `bots:` list is given). Results are saved to `all_games.yaml` and a static HTML report is written to `report_site/`.

# Experiments

This is a multiplayer game, so it's complex to have a general score to associate with a bot. However, we can rely on a relative value (a bot's strength also depends on its opponents), and it's also possible to see which bots each one performs well against. My strategy for evaluating the bots is to play a very large number of games (1 million) and collect statistics along the way (see `experiments/runner.py` and `experiments/stats.py`).

The primary ranking metric is **Score = hard wins + 0.5 × soft wins**, where a *hard win* is finishing first and a *soft win* is any other finish that escapes the final losing pair.

## Bots

Each bot lives in its own file under `bots/manual/` (hand-written strategies) and `bots/llms/` (strategies authored by LLMs), with its strategy documented in the class docstring. The report site contains a per-bot page with win rates, behavioral stats, and neighbor matchups.

# Report

`python -m experiments` generates the report site after playing the games. To rebuild the site from saved results without replaying anything:

```bash
python -m experiments.report                                # all_games.yaml → report_site/
python -m experiments.report results/all_games.yaml --config results/experiment.yaml
```

## Publish the report on GitHub Pages

The final report is published from the committed snapshot in `results/` (`all_games.yaml` plus the `experiment.yaml` it was produced with) by the `Publish report` workflow (`.github/workflows/report.yml`), which rebuilds the site in CI and deploys it to GitHub Pages.

One-time setup: repo **Settings → Pages → Source: "GitHub Actions"**. After that, the report republishes automatically whenever `results/` changes on `main` (or on demand from the Actions tab via *Run workflow*).

To publish a new final report: run the experiment, refresh the snapshot, and push:

```bash
python -m experiments
cp all_games.yaml experiment.yaml results/
```

# Final Conclusion

- The game heavily depends on the chosen **position** at the beginning of the match and consequently on the players preceding and succeeding you.
- There is a clear split between "**aggressive**" bots (with a tendency to bluff) and "**passive**" bots (inclined to play honestly: doubting and playing cards associated with the correct number). Aggressive bots exhibit greater variance in win rate concerning succeeding players, while passive bots show more variance concerning preceding players.
- Luck and position matter, but they are **not the whole story**: the current champion is **ClaudeFableBot** (`bots/llms/claude_fable.py`), which wins decisively both in the full field and in a top-5-only field. It combines exact card tracking (revealed pile pickups, discards, its own pile contributions), Beta-smoothed opponent bluff/doubt models, a hypergeometric feasibility check on every claim, and expected-value action selection — plus an engine-exact endgame: a hand-emptying play can never be doubted, so reaching ≤3 cards through un-doubtable plays is a guaranteed win.
