from core_game import dubito
from tqdm import tqdm
from pprint import pprint
import random
from bots import rule_based, probability
import csv

ALGORITHMS = [
    rule_based.AlwaysTruthful,
    rule_based.JustPutCards,
    rule_based.MrDoubt,
    rule_based.MrNoDoubt,
    rule_based.RandomBoi,
    probability.AdptyBoi,
    probability.SusBoi,
    probability.UsualBot,
    probability.RiskCounter,
]
PLAYERS_NUMBER = 6
N_EXPERIMENTS = 10_000

players_alg = set([a.__name__ for a in ALGORITHMS])
final_infos = {}

csv_path = 'machine_learning\dataset.csv'
header = ['hand', 'board_cards', 'playing_cards', 'current_number', 'n_cards_played', 'streak',
          'prev_turns', 'prev_not_first_turns', 'prev_doubts', 'prev_honest_times', 'prev_dishonest_times', 'prev_n_cards',
          'next_turns', 'next_not_first_turns', 'next_doubts', 'next_honest_times', 'next_dishonest_times', 'next_n_cards',
          'output_doubt', 'output_cards', 'output_number', 'target']

with open(csv_path, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(header)
    for i in tqdm(range(N_EXPERIMENTS), desc = "Playing Games"):
        
        all_players = []
        
        for i in range(1, PLAYERS_NUMBER + 1):
            random_algorithm = random.choice(ALGORITHMS)
            all_players.append(random_algorithm(i))
        
        _, info = dubito(all_players)
        for move in info['decisions']:
            writer.writerow(move)

