import sys

from .runner import ALL_BOTS, load_config, save_stats, print_summary, play_games
from .report import generate_html_site


if __name__ == '__main__':
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'experiment.yaml'
    config = load_config(config_path)

    bot_names         = config.get('bots', list(ALL_BOTS.keys()))
    algorithms        = [ALL_BOTS[name] for name in bot_names]
    available_players = config['available_players']
    n_experiments     = config['n_experiments']
    output_file = config.get('output_file', 'all_games.yaml')
    output_dir  = config.get('output_dir', 'report_site')

    print(f"Running {n_experiments:,} games with {len(algorithms)} bots "
          f"and {available_players[0]}–{available_players[-1]} players per game.")

    final_infos = play_games(algorithms, available_players, n_experiments)

    save_stats(final_infos, output_file)
    print(f"\nResults saved to {output_file}")

    print_summary(final_infos)

    print('\nGenerating HTML site...')
    generate_html_site(final_infos, config, output_dir)
