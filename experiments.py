from core_game import dubito
from tqdm import tqdm
from pprint import pprint
import random
from bots import rule_based, probability
from typing import Dict, List
from player import Player
import yaml
import copy

def save_stats(stats: Dict, data_name: str = "all_games.yaml") -> None:
    """Save game statistics to a YAML file."""
    with open(data_name, 'w') as yaml_file:
        yaml.dump(stats, yaml_file, allow_unicode=True)

ALGORITHMS = [
    rule_based.AlwaysTruthful,
    rule_based.JustPutCards,
    rule_based.MrDoubt,
    rule_based.MrNoDoubt,
    rule_based.RandomBoi,
    rule_based.StefaBot,
    probability.AdptyBoi,
    probability.SusBoi,
    probability.UsualBot,
    probability.RiskCounter,
]

AVAILABLE_PLAYERS = list(range(3, 8))
N_EXPERIMENTS = 1_000

def play_games(ALGORITHMS: List, AVAILABLE_PLAYERS: List[int], N_EXPERIMENTS: int) -> Dict:
    """Simulate multiple games and collect statistics."""
    players_alg = set([a.__name__ for a in ALGORITHMS])
    final_infos = {}

    placeholder_data = {
        'games': 0,
        'prev': {alg: 0 for alg in players_alg},
        'next': {alg: 0 for alg in players_alg},
        'avg_cards': .0,
    }

    for p_alg in players_alg:
        final_infos[p_alg] = {
            'total': copy.deepcopy(placeholder_data),
            'wins': copy.deepcopy(placeholder_data),
            'losses': copy.deepcopy(placeholder_data),
        }

    for _ in tqdm(range(N_EXPERIMENTS), desc="Playing Games ..."):
        player_number = random.choice(AVAILABLE_PLAYERS)
        all_players: List[Player] = []

        for i in range(1, player_number + 1):
            random_algorithm = random.choice(ALGORITHMS)
            all_players.append(random_algorithm(i))

        results, _ = dubito(all_players)
        for idx, p in enumerate(all_players):
            result = 'losses' if p not in results['winners'] else 'wins'

            final_infos[p.__class__.__name__]['total']['games'] += 1
            final_infos[p.__class__.__name__]['total']['prev'][all_players[(idx - 1) % len(all_players)].__class__.__name__] += 1
            final_infos[p.__class__.__name__]['total']['next'][all_players[(idx + 1) % len(all_players)].__class__.__name__] += 1
            final_infos[p.__class__.__name__]['total']['avg_cards'] += len(p.cards)

            final_infos[p.__class__.__name__][result]['games'] += 1
            final_infos[p.__class__.__name__][result]['prev'][all_players[(idx - 1) % len(all_players)].__class__.__name__] += 1
            final_infos[p.__class__.__name__][result]['next'][all_players[(idx + 1) % len(all_players)].__class__.__name__] += 1
            final_infos[p.__class__.__name__][result]['avg_cards'] += len(p.cards)

    for p_alg in players_alg:
        keys = list(final_infos[p_alg].keys())
        for key in keys:
            final_infos[p_alg][key]['avg_cards'] = final_infos[p_alg][key]['avg_cards'] / final_infos[p_alg][key]['games']

    return final_infos

final_infos = play_games(ALGORITHMS, AVAILABLE_PLAYERS, N_EXPERIMENTS)
pprint(final_infos)
save_stats(final_infos)
