#!/usr/bin/env python3
"""
app.py — Flask web backend for Dubito.
Run:  python3 app.py
Deps: pip install flask
"""
import random
import uuid

from flask import Flask, jsonify, render_template, request

from dubito.player import Player
from dubito.handlers import GameHandler, generate_player_data
from dubito.game_data import (
    TurnOutput, TurnData,
    GameStartEvent, CardsPlayedEvent, DoubtResolvedEvent, DiscardEvent, PlayerWonEvent,
)
from dubito.core_game import initialize
import bots  # noqa: F401 — populates BotBase.registry
from bots.base import BotBase

app = Flask(__name__)

ALL_BOTS: dict[str, type] = BotBase.registry


# ── Card name helpers ─────────────────────────────────────────────────────────

NAMES = {0: "★", 1: "A", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6",
         7: "7", 8: "8", 9: "9", 10: "10", 11: "J", 12: "Q", 13: "K"}
LONG  = {0: "Joker", 1: "Ace", 11: "Jack", 12: "Queen", 13: "King"}

def cn(v):  return NAMES.get(v, str(v))
def cln(v): return LONG.get(v, cn(v))


# ── Human player ──────────────────────────────────────────────────────────────

class HumanPlayer(Player):
    def play(self, p: TurnData) -> TurnOutput:
        raise NotImplementedError("Human player plays via the web UI")

    def add_cards(self, cards: list[int]) -> None:
        # Append in arrival order — no sorting, so the player sees exactly
        # which cards they just picked up.
        self.cards.hand.extend(cards)


# ── In-memory session store ───────────────────────────────────────────────────

_sessions: dict[str, "GameSession"] = {}


# ── Game session ──────────────────────────────────────────────────────────────

class GameSession:
    """Manages a single interactive game between one human and N bots."""

    def __init__(self, all_players: list[Player], show_names: bool) -> None:
        self.id           = str(uuid.uuid4())[:8]
        self.gh           = GameHandler(all_players=all_players, deck_size=14)
        self.human        = next(p for p in all_players if isinstance(p, HumanPlayer))
        self.all_players  = all_players
        self.prev_player  = all_players[-1]
        self.this_player  = all_players[0]
        self.show_names   = show_names
        self.messages: list[str] = []
        self._correct_doubt = False
        self.gh.append_event(GameStartEvent(
            player_ids=[p.id for p in all_players],
            initial_card_counts={p.id: len(p.cards) for p in all_players},
        ))

    # ── Label helpers ─────────────────────────────────────────────────────────

    def _lbl(self, p: Player) -> str:
        if isinstance(p, HumanPlayer):
            return "You"
        return p.__class__.__name__ if self.show_names else f"Bot {p.id}"

    def _display_name(self, p: Player) -> str:
        if isinstance(p, HumanPlayer):
            return "YOU"
        return p.__class__.__name__ if self.show_names else f"Bot {p.id}"

    # ── Board snapshot ────────────────────────────────────────────────────────

    def snap(self) -> dict:
        """Lightweight snapshot of board state + card counts + human hand."""
        gh = self.gh
        return {
            "board_cards":      gh.n_cards_board(),
            "last_n_played":    len(gh.board.latests) if gh.board.latests else 0,
            "declared_number":  gh.board.number if gh.board.number else None,
            "declared_name":    cln(gh.board.number) if gh.board.number else None,
            "is_first_hand":    gh.is_first_hand(),
            "players_cards":    {str(p.id): len(p.cards) for p in self.all_players},
            "human_hand":       list(self.human.cards.hand),
        }

    # ── Output resolution ─────────────────────────────────────────────────────

    def process_output(
        self, output: TurnOutput, this_player: Player, prev_player: Player
    ) -> tuple[list[dict], bool]:
        """
        Apply a TurnOutput to the game state.

        Returns:
            resolve_events: frame dicts for doubt resolution, discards, and wins.
            correct_doubt:  True when the doubter was right (they earn a free turn).
        """
        gh = self.gh
        resolve_events: list[dict] = []
        correct_doubt = False

        if output.doubt:
            latest_cards  = list(gh.get_latest_played_cards())
            board_snap    = list(gh.get_board())
            declared_snap = gh.get_current_number()
            revealed = ', '.join(cn(c) for c in latest_cards)
            jokers = gh.jokers_in_latest()
            takes = "take" if isinstance(this_player, HumanPlayer) else "takes"

            if gh.is_honest() and jokers:
                rest = [c for c in gh.get_board() if c != 0]
                this_player.add_cards(rest)
                gh.reset_board()
                gh.append_event(DoubtResolvedEvent(
                    doubter_id=this_player.id, target_id=prev_player.id, correct=False,
                    latest_cards=latest_cards, board_cards=rest,
                    declared_number=declared_snap, jokers_discarded=len(jokers),
                ))
                resolve_events.append({
                    "msg": (
                        f"Joker! {self._lbl(prev_player)} played [{revealed}] — protected. "
                        f"{self._lbl(this_player)} {takes} {len(rest)} card(s)."
                    ),
                    "event_type": "joker",
                    "actor_id":   this_player.id,
                    "target_id":  this_player.id,
                    "revealed_cards": latest_cards,
                    **self.snap(),
                })
            elif gh.is_honest():
                n = gh.n_cards_board()
                this_player.add_cards(gh.get_board())
                gh.reset_board()
                gh.append_event(DoubtResolvedEvent(
                    doubter_id=this_player.id, target_id=prev_player.id, correct=False,
                    latest_cards=latest_cards, board_cards=board_snap,
                    declared_number=declared_snap,
                ))
                resolve_events.append({
                    "msg": (
                        f"{self._lbl(prev_player)} was honest — played [{revealed}]. "
                        f"{self._lbl(this_player)} takes {n} card(s). Ouch."
                    ),
                    "event_type": "take_honest",
                    "actor_id":   this_player.id,
                    "target_id":  this_player.id,
                    "revealed_cards": latest_cards,
                    **self.snap(),
                })
            else:
                n = gh.n_cards_board()
                correct_doubt = True
                prev_player.add_cards(gh.get_board())
                gh.reset_board()
                gh.append_event(DoubtResolvedEvent(
                    doubter_id=this_player.id, target_id=prev_player.id, correct=True,
                    latest_cards=latest_cards, board_cards=board_snap,
                    declared_number=declared_snap,
                ))
                resolve_events.append({
                    "msg": (
                        f"{self._lbl(prev_player)} was bluffing — actually played [{revealed}]. "
                        f"They take {n} card(s). Free turn for {self._lbl(this_player)}!"
                    ),
                    "event_type": "take_bluff",
                    "actor_id":   this_player.id,
                    "target_id":  prev_player.id,
                    "revealed_cards": latest_cards,
                    **self.snap(),
                })
        else:
            if gh.is_first_hand():
                val = output.number or 1
                if val == 0:
                    pool = gh.board.availables or output.cards
                    val = random.choice(pool)
                gh.set_current_number(val)
            gh.set_board_cards(output.cards)
            gh.append_event(CardsPlayedEvent(
                player_id=this_player.id,
                declared_number=gh.get_current_number(),
                n_cards=len(output.cards),
            ))

        # Discard phase
        for p in gh.playing_players():
            disc = p.discard_cards()
            if disc:
                gh.set_discarded_cards(disc)
                for number in disc:
                    gh.append_event(DiscardEvent(player_id=p.id, card_number=number))
                    resolve_events.append({
                        "msg":        f"{self._lbl(p)} discards four {cn(number)}s.",
                        "event_type": "discard",
                        "actor_id":   p.id,
                        "target_id":  p.id,
                        **self.snap(),
                    })

        # Win check
        for winner in [p for p in gh.playing_players() if p.has_no_cards()]:
            gh.set_winners(winner)
            gh.append_event(PlayerWonEvent(player_id=winner.id, position=gh.n_winners_players()))
            resolve_events.append({
                "msg":        f"{self._lbl(winner)} wins!",
                "event_type": "win",
                "actor_id":   winner.id,
                "target_id":  winner.id,
                **self.snap(),
            })
        if gh.n_playing_players() == 2:
            losers = gh.playing_players()
            resolve_events.append({
                "msg":        f"Game over — {self._lbl(losers[0])} and {self._lbl(losers[1])} lose!",
                "event_type": "game_over",
                "actor_id":   None,
                "target_id":  None,
                **self.snap(),
            })

        return resolve_events, correct_doubt

    # ── Bot auto-play ─────────────────────────────────────────────────────────

    def advance_bots(self) -> list[dict]:
        """
        Auto-play all consecutive bot turns until it's the human's turn (or game over).
        Returns animation frames, one per game event.
        """
        gh = self.gh
        all_frames: list[dict] = []

        while True:
            if gh.n_playing_players() <= 2 or gh.turn.counter >= 1000:
                break

            if self._correct_doubt:
                self._correct_doubt = False
            else:
                self.prev_player, self.this_player = gh.next_turn()

            this_player = self.this_player
            if isinstance(this_player, HumanPlayer):
                break

            ip = generate_player_data(gh)
            is_first = gh.is_first_hand()
            output = this_player.play(ip)

            if output.doubt:
                pre_snap = self.snap()
                resolve_events, correct_doubt = self.process_output(output, this_player, self.prev_player)
                doubt_msg = f"{self._lbl(this_player)} doubts {self._lbl(self.prev_player)}!"
                self.messages.append(doubt_msg)
                all_frames.append({
                    "msg":        doubt_msg,
                    "event_type": "doubt",
                    "actor_id":   this_player.id,
                    "target_id":  self.prev_player.id,
                    **pre_snap,
                })
            else:
                resolve_events, correct_doubt = self.process_output(output, this_player, self.prev_player)
                play_msg = (
                    f"{self._lbl(this_player)} plays {len(output.cards)} card(s), "
                    f"declares {cln(output.number)}s."
                    if is_first else
                    f"{self._lbl(this_player)} plays {len(output.cards)} card(s) "
                    f"claiming {cln(gh.board.number)}s."
                )
                self.messages.append(play_msg)
                all_frames.append({
                    "msg":        play_msg,
                    "event_type": "play",
                    "actor_id":   this_player.id,
                    "target_id":  None,
                    **self.snap(),
                })

            for e in resolve_events:
                self.messages.append(e["msg"])
                all_frames.append(e)

            self._correct_doubt = correct_doubt

        return all_frames

    # ── Human actions ─────────────────────────────────────────────────────────

    def play_cards(self, card_indices: list[int], number: int | None) -> list[dict]:
        """Execute a human play. Returns all animation frames."""
        gh = self.gh
        is_first = gh.is_first_hand()

        cards = [self.human.cards.hand[i] for i in card_indices]
        for i in sorted(card_indices, reverse=True):
            self.human.cards.hand.pop(i)

        if is_first:
            play_msg = f"You play {len(cards)} card(s) and declare {cln(number)}s."
            output = TurnOutput(doubt=False, number=number, cards=cards)
        else:
            play_msg = f"You play {len(cards)} card(s) claiming {cln(gh.board.number)}s."
            output = TurnOutput(doubt=False, number=None, cards=cards)

        resolve_events, correct_doubt = self.process_output(output, self.human, self.prev_player)

        self.messages.append(play_msg)
        frames: list[dict] = [{
            "msg":        play_msg,
            "event_type": "play",
            "actor_id":   self.human.id,
            "target_id":  None,
            **self.snap(),
        }]
        for e in resolve_events:
            self.messages.append(e["msg"])
            frames.append(e)

        self._correct_doubt = correct_doubt
        return frames + self.advance_bots()

    def call_doubt(self) -> list[dict]:
        """Execute a human doubt. Returns all animation frames."""
        pre_snap  = self.snap()
        doubt_msg = f"You doubt {self._lbl(self.prev_player)}!"
        output    = TurnOutput(doubt=True, number=None, cards=None)
        resolve_events, correct_doubt = self.process_output(output, self.human, self.prev_player)

        self.messages.append(doubt_msg)
        frames: list[dict] = [{
            "msg":        doubt_msg,
            "event_type": "doubt",
            "actor_id":   self.human.id,
            "target_id":  self.prev_player.id,
            **pre_snap,
        }]
        for e in resolve_events:
            self.messages.append(e["msg"])
            frames.append(e)

        self._correct_doubt = correct_doubt
        return frames + self.advance_bots()

    # ── Serialization ─────────────────────────────────────────────────────────

    def serialize(self) -> dict:
        """Return a JSON-serializable snapshot of the full game state."""
        gh      = self.gh
        playing = gh.playing_players()
        winners = gh.get_winners()
        is_over = gh.n_playing_players() <= 2 or gh.turn.counter >= 1000

        players_info = [
            {
                "id":           p.id,
                "display_name": self._display_name(p),
                "is_human":     isinstance(p, HumanPlayer),
                "n_cards":      len(p.cards),
                "is_current":   p is self.this_player,
                "is_prev":      p is self.prev_player and p is not self.this_player,
                "is_playing":   p in playing or p in winners,
            }
            for p in self.all_players
        ]

        winner_set  = set(winners)
        non_winners = sorted(
            [p for p in gh.playing_players() if p not in winner_set],
            key=lambda p: len(p.cards),
        )
        standings = [
            {"name": self._display_name(w), "bot_type": None if isinstance(w, HumanPlayer) else w.__class__.__name__, "cards": 0,          "is_human": isinstance(w, HumanPlayer)}
            for w in winners
        ] + [
            {"name": self._display_name(p), "bot_type": None if isinstance(p, HumanPlayer) else p.__class__.__name__, "cards": len(p.cards), "is_human": isinstance(p, HumanPlayer)}
            for p in non_winners
        ]

        return {
            "game_id":          self.id,
            "status":           "game_over" if is_over else "player_turn",
            "turn":             gh.turn.counter,
            "is_first_hand":    gh.is_first_hand(),
            "board_cards":      gh.n_cards_board(),
            "last_n_played":    len(gh.board.latests) if gh.board.latests else 0,
            "declared_number":  gh.board.number if gh.board.number else None,
            "declared_name":    cln(gh.board.number) if gh.board.number else None,
            "streak":           gh.turn.streak,
            "available_numbers": gh.board.availables,
            "hand":             list(self.human.cards.hand),
            "players":          players_info,
            "messages":         self.messages,
            "standings":        standings,
            "timed_out":        gh.turn.counter >= 1000,
        }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/bots")
def api_bots():
    return jsonify(list(ALL_BOTS.keys()))


@app.route("/api/game", methods=["POST"])
def api_create_game():
    body       = request.get_json(force=True)
    n_players  = max(3, min(8, int(body.get("n_players", 4))))
    bot_pool   = body.get("bot_pool", list(ALL_BOTS.keys()))
    show_names = bool(body.get("show_names", True))

    pool = [ALL_BOTS[n] for n in bot_pool if n in ALL_BOTS] or list(ALL_BOTS.values())
    human = HumanPlayer(1)
    bots  = [random.choice(pool)(i + 2) for i in range(n_players - 1)]
    all_players = [human] + bots
    random.shuffle(all_players)
    for i, p in enumerate(all_players):
        p.id = i + 1

    initialize(all_players, n_jollies=2)

    session = GameSession(all_players, show_names)
    _sessions[session.id] = session

    init_frames = session.advance_bots()
    return jsonify(session.serialize() | {"frames": init_frames})


@app.route("/api/game/<gid>/play", methods=["POST"])
def api_play(gid: str):
    session = _sessions.get(gid)
    if not session:
        return jsonify({"error": "game not found"}), 404

    body         = request.get_json(force=True)
    card_indices = sorted(body.get("card_indices", []))
    number       = body.get("number", None)

    if not card_indices:
        return jsonify({"error": "no cards selected"}), 400

    frames = session.play_cards(card_indices, number)
    return jsonify(session.serialize() | {"frames": frames})


@app.route("/api/game/<gid>/doubt", methods=["POST"])
def api_doubt(gid: str):
    session = _sessions.get(gid)
    if not session:
        return jsonify({"error": "game not found"}), 404

    if session.gh.is_first_hand():
        return jsonify({"error": "cannot doubt on first hand"}), 400

    frames = session.call_doubt()
    return jsonify(session.serialize() | {"frames": frames})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(port=5001, debug=True)
