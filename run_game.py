"""
Run a single game of Dubito from the command line.

Usage:
    python3 run_game.py              # default 4 bots
    python3 run_game.py --logs       # print full turn-by-turn log
    python3 run_game.py --players AlwaysTruthful MrDoubt RandomBoi MrNoDoubt
    python3 run_game.py --players RandomBoi RandomBoi RandomBoi --logs
"""

import argparse
from dubito.core_game import dubito
import bots  # noqa: F401 — side-effect import: registers all subclasses in BotBase.registry
from bots.base import BotBase

BOTS = BotBase.registry

DEFAULT_PLAYERS = ["AlwaysTruthful", "MrNoDoubt", "MrDoubt", "RandomBoi"]


def main():
    parser = argparse.ArgumentParser(description="Run a single game of Dubito.")
    parser.add_argument(
        "--players", nargs="+", default=DEFAULT_PLAYERS,
        metavar="BOT",
        help=f"Bot names (3–8). Available: {', '.join(BOTS)}",
    )
    parser.add_argument("--logs", action="store_true", help="Print full turn-by-turn log.")
    parser.add_argument("--no-shuffle", action="store_true", help="Keep players in the given order.")
    parser.add_argument("--jollies", type=int, default=2, metavar="N", help="Number of joker cards (default 2).")
    args = parser.parse_args()

    if not (3 <= len(args.players) <= 8):
        parser.error("Need between 3 and 8 players.")

    unknown = [name for name in args.players if name not in BOTS]
    if unknown:
        parser.error(f"Unknown bot(s): {', '.join(unknown)}. Choose from: {', '.join(BOTS)}")

    players = [BOTS[name](i + 1) for i, name in enumerate(args.players)]

    print(f"Starting game with: {', '.join(args.players)}")
    print(f"Jokers: {args.jollies}  |  Shuffle: {not args.no_shuffle}\n")

    result, infos = dubito(
        all_players=players,
        shuffle_players=not args.no_shuffle,
        n_jollies=args.jollies,
    )

    if args.logs:
        print(infos["logs"])
        print()

    winners = [f"Player{p.id} ({p.__class__.__name__})" for p in result["winners"]]
    losers  = [f"Player{p.id} ({p.__class__.__name__})" for p in result["losers"]]

    print("=== Result ===")
    for rank, name in enumerate(winners, start=1):
        print(f"  #{rank}  {name}")
    for name in losers:
        print(f"  L   {name}")


if __name__ == "__main__":
    main()
