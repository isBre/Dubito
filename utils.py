import yaml
import players_algorithm

def players_from_yaml():
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)
    players = []
    for i, p in enumerate(config['players'], 1):
        player_type = getattr(players_algorithm, p)
        players.append(player_type(i))
    return players