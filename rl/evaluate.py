"""
Benchmark RLBot against all rule-based and probability bots.

Usage:
    python rl/evaluate.py                             # uses rl/models/best_model.zip
    python rl/evaluate.py --model rl/models/ppo_dubito.zip
    python rl/evaluate.py --games 5000
"""

import argparse
import os
import sys
import random
import copy
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stable_baselines3 import PPO
from rl.bot import RLBot
from bots import rule_based, probability
from dubito.core_game import dubito


ALL_OPPONENTS = {
    "AlwaysTruthful": rule_based.AlwaysTruthful,
    "JustPutCards":   rule_based.JustPutCards,
    "MrDoubt":        rule_based.MrDoubt,
    "MrNoDoubt":      rule_based.MrNoDoubt,
    "RandomBoi":      rule_based.RandomBoi,
    "StefaBot":       rule_based.StefaBot,
    "AdaptyBoi":      probability.AdaptyBoi,
    "SusBoi":         probability.SusBoi,
    "UsualBot":       probability.UsualBot,
    "RiskCounter":    probability.RiskCounter,
}


def evaluate(model_path: str, n_games: int) -> None:
    # pre-load the model into RLBot class cache
    RLBot._model = PPO.load(model_path)

    results: dict[str, dict] = {}   # opponent → {wins, games}

    opponent_list = list(ALL_OPPONENTS.values())
    available_players = [3, 4, 5, 6, 7]

    wins = 0
    total = 0

    for _ in tqdm(range(n_games), desc="Evaluating", unit="game"):
        n_players = random.choice(available_players)
        rl_agent  = RLBot(1)
        opponents = [random.choice(opponent_list)(i + 2) for i in range(n_players - 1)]
        all_players = [rl_agent] + opponents
        random.shuffle(all_players)
        for i, p in enumerate(all_players, 1):
            p.id = i

        results_game, _ = dubito(all_players)
        rl_won = rl_agent in results_game["winners"]
        wins  += int(rl_won)
        total += 1

        for opp in opponents:
            name = opp.__class__.__name__
            if name not in results:
                results[name] = {"wins": 0, "games": 0}
            results[name]["games"] += 1
            if rl_won:
                results[name]["wins"] += 1

    # ── print summary ──────────────────────────────────────────────────────────
    col = 18
    header = f"{'Opponent':<{col}} {'Games':>8} {'RLBot Win%':>12}"
    sep = "=" * len(header)
    print(f"\n{sep}")
    print(f"RLBot Evaluation — {model_path}")
    print(f"Overall: {wins}/{total} = {wins/total:.1%} win rate across all games")
    print(sep)
    print(header)
    print("-" * len(header))
    rows = sorted(results.items(), key=lambda x: x[1]["wins"] / x[1]["games"], reverse=True)
    for name, r in rows:
        wr = r["wins"] / r["games"]
        print(f"{name:<{col}} {r['games']:>8} {wr:>11.1%}")
    print(sep)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="rl/models/best_model.zip")
    parser.add_argument("--games", type=int, default=2000)
    args = parser.parse_args()
    evaluate(args.model, args.games)
