import yaml
import matplotlib.pyplot as plt
import numpy as np

# Step 1: Parse YAML file
with open("all_games.yaml", "r") as file:
    data = yaml.safe_load(file)

# Step 2: Calculate win rates
players = data.keys()
win_rates = {}
for player in players:
    total_games = data[player]['total']['games']
    total_wins = data[player]['wins']['games']
    win_rates[player] = total_wins / total_games

# Step 3: Plot bar graph with win rate
plt.figure(figsize=(10, 6))
bars = plt.bar(win_rates.keys(), win_rates.values())
plt.ylabel('Win Rate')
plt.title('Win Rate of Players')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.xticks(rotation=45)

# Add values on top of the bars
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2 - 0.3, yval, round(yval, 4), va='bottom')  # Vertically align text bottom

# Add a dotted red line at y = 1/number of players
num_players = len(players)
y_line = 1 / num_players
plt.axhline(y=y_line, color='red', linestyle='--')

plt.tight_layout()
plt.savefig('graphs/win_rate_bar_graph.png')

# Step 3.1 Plot bar graph with avg cards in the hand
avg_cards = [data[player]['total']['avg_cards'] for player in players]

plt.figure(figsize=(10, 6))
bars = plt.bar(players, avg_cards)
plt.ylabel('Average Total Cards')
plt.title('Average Card Total Per Player')
plt.xticks(rotation=45)
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Add values on top of the bars
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2 - 0.15, yval, round(yval, 2), va='bottom')  # Vertically align text bottom

plt.tight_layout()
plt.savefig('graphs/avg_cards_bar_graph.png')

# Step 4: Plot bar graph for each player with win rate compared to players positioned prev and next
for player in players:
    plt.figure(figsize=(14, 6))

    # Win rate compared with players positioned prev
    prev_win_rates = {}
    for prev_player in data[player]['losses']['prev']:
        if prev_player != player:
            total_games = data[player]['losses']['prev'][prev_player] + data[player]['wins']['prev'][prev_player]
            total_wins = data[player]['wins']['prev'][prev_player]
            prev_win_rates[prev_player] = total_wins / total_games
    plt.subplot(1, 2, 1)
    bars = plt.bar(prev_win_rates.keys(), prev_win_rates.values())
    plt.xlabel('Players')
    plt.ylabel('Win Rate')
    plt.title(f'Win Rate of {player} compared to players positioned prev')
    plt.xticks(rotation=45)
    plt.ylim(0, 1)  # Setting y-axis limit
    # Add values on top of the bars
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2 - 0.15, yval, round(yval, 2), va='bottom')  # Vertically align text bottom

    # Win rate compared with players positioned next
    next_win_rates = {}
    for next_player in data[player]['losses']['next']:
        if next_player != player:
            total_games = data[player]['losses']['next'][next_player] + data[player]['wins']['next'][next_player]
            total_wins = data[player]['wins']['next'][next_player]
            next_win_rates[next_player] = total_wins / total_games
    plt.subplot(1, 2, 2)
    bars = plt.bar(next_win_rates.keys(), next_win_rates.values())
    plt.xlabel('Players')
    plt.ylabel('Win Rate')
    plt.title(f'Win Rate of {player} compared to players positioned next')
    plt.xticks(rotation=45)
    plt.ylim(0, 1)  # Setting y-axis limit
    # Add values on top of the bars
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2 - 0.15, yval, round(yval, 2), va='bottom')  # Vertically align text bottom

    plt.tight_layout()
    plt.savefig(f'graphs/{player}_win_rate_comparison.png')

# Close all figures to avoid memory leaks
plt.close('all')
