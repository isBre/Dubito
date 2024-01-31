from core_game import game
from tqdm import tqdm
from pprint import pprint
from utils import players_from_yaml

all_players = players_from_yaml()
players_alg = set([p.__class__.__name__ for p in all_players])
final_infos = {}
for p in all_players:
    final_infos[p.id] = {'type' : p.__class__.__name__,
                         'stats' : {
                             'wins' : {
                                 'total' : 0,
                                 'position' : {idx : 0 for idx, _ in enumerate(all_players, 1)},
                                 'prev' : {alg : 0 for alg in players_alg},
                                 'next' : {alg : 0 for alg in players_alg},
                             },
                             'losses' : {
                                 'total' : 0,
                                 'position' : {idx : 0 for idx, _ in enumerate(all_players, 1)},
                                 'prev' : {alg : 0 for alg in players_alg},
                                 'next' : {alg : 0 for alg in players_alg},
                             }
                        }
                        }

for i in tqdm(range(10000), desc = "Playing Games"):
    winners, losers = game(all_players, verbose = 0)
    for idx, p in enumerate(all_players):

        result = 'losses'
        if p in winners:
            result = 'wins'

        final_infos[p.id]['stats'][result]['total'] += 1
        final_infos[p.id]['stats'][result]['position'][p.game_position] += 1
        final_infos[p.id]['stats'][result]['prev'][all_players[(idx - 1) % len(all_players) - 1].__class__.__name__] += 1
        final_infos[p.id]['stats'][result]['next'][all_players[(idx + 1) % len(all_players) - 1].__class__.__name__] += 1

pprint(final_infos)