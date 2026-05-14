from dubito.core_game import dubito
from dubito.player import Player
from tqdm import tqdm
import random
import yaml
import copy
import subprocess
import sys
from bots import rule_based, probability


ALL_BOTS = {
    'AlwaysTruthful': rule_based.AlwaysTruthful,
    'JustPutCards':   rule_based.JustPutCards,
    'MrDoubt':        rule_based.MrDoubt,
    'MrNoDoubt':      rule_based.MrNoDoubt,
    'RandomBoi':      rule_based.RandomBoi,
    'StefaBot':       rule_based.StefaBot,
    'AdaptyBoi':      probability.AdaptyBoi,
    'SusBoi':         probability.SusBoi,
    'UsualBot':       probability.UsualBot,
    'RiskCounter':    probability.RiskCounter,
}


def load_config(path: str = 'experiment.yaml') -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def save_stats(stats: dict, path: str) -> None:
    with open(path, 'w') as f:
        yaml.dump(stats, f, allow_unicode=True)


def print_summary(final_infos: dict) -> None:
    col = 20
    header = f"{'Bot':<{col}} {'Games':>8} {'Win%':>8} {'Avg Cards':>10}"
    sep = '=' * len(header)
    print(f'\n{sep}')
    print('Experiment Results')
    print(sep)
    print(header)
    print('-' * len(header))
    rows = [
        (
            info['wins']['games'] / info['total']['games'] * 100,
            bot,
            info['total']['games'],
            info['total']['avg_cards'],
        )
        for bot, info in final_infos.items()
        if info['total']['games'] > 0
    ]
    for win_pct, bot, total, avg_cards in sorted(rows, reverse=True):
        print(f"{bot:<{col}} {total:>8} {win_pct:>7.1f}% {avg_cards:>10.2f}")
    print(sep)


def play_games(algorithms: list, available_players: list[int], n_experiments: int) -> dict:
    players_alg = {a.__name__ for a in algorithms}

    placeholder = {
        'games': 0,
        'prev': {alg: 0 for alg in players_alg},
        'next': {alg: 0 for alg in players_alg},
        'avg_cards': 0.0,
    }

    final_infos = {
        alg: {
            'total':  copy.deepcopy(placeholder),
            'wins':   copy.deepcopy(placeholder),
            'losses': copy.deepcopy(placeholder),
        }
        for alg in players_alg
    }

    for _ in tqdm(range(n_experiments), desc='Playing Games', unit='game'):
        player_number = random.choice(available_players)
        all_players: list[Player] = [
            random.choice(algorithms)(i)
            for i in range(1, player_number + 1)
        ]

        results, _ = dubito(all_players)
        n = len(all_players)

        for idx, p in enumerate(all_players):
            name = p.__class__.__name__
            outcome = 'wins' if p in results['winners'] else 'losses'
            prev_name = all_players[(idx - 1) % n].__class__.__name__
            next_name = all_players[(idx + 1) % n].__class__.__name__

            for bucket in ('total', outcome):
                final_infos[name][bucket]['games'] += 1
                final_infos[name][bucket]['prev'][prev_name] += 1
                final_infos[name][bucket]['next'][next_name] += 1
                final_infos[name][bucket]['avg_cards'] += len(p.cards)

    for alg in players_alg:
        for bucket in ('total', 'wins', 'losses'):
            g = final_infos[alg][bucket]['games']
            if g > 0:
                final_infos[alg][bucket]['avg_cards'] /= g

    return final_infos


if __name__ == '__main__':
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'experiment.yaml'
    config = load_config(config_path)

    bot_names = config.get('bots', list(ALL_BOTS.keys()))
    algorithms = [ALL_BOTS[name] for name in bot_names]
    available_players = config['available_players']
    n_experiments = config['n_experiments']
    output_file = config.get('output_file', 'all_games.yaml')
    run_graphs = config.get('run_graphs', False)

    print(f"Running {n_experiments:,} games with {len(algorithms)} bots "
          f"and {available_players[0]}–{available_players[-1]} players per game.")

    final_infos = play_games(algorithms, available_players, n_experiments)

    save_stats(final_infos, output_file)
    print(f"\nResults saved to {output_file}")

    print_summary(final_infos)

    if run_graphs:
        print('\nGenerating graphs...')
        subprocess.run([sys.executable, 'assets/graphs/stats.py'], check=True)
        print('Graphs updated.')
