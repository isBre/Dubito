"""
Regenerate the HTML report site from saved experiment results — no games are played.

Usage:
    python -m experiments.report                                # all_games.yaml → report_site/
    python -m experiments.report results/all_games.yaml --config results/experiment.yaml
"""
import argparse

import yaml

from ..stats import BotStats, BucketStats
from . import generate_html_site


def load_stats(path: str) -> dict[str, BotStats]:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return {
        bot: BotStats(**{bucket: BucketStats(**values) for bucket, values in buckets.items()})
        for bot, buckets in raw.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', nargs='?', default='all_games.yaml',
                        help='results YAML produced by python -m experiments')
    parser.add_argument('--config', default='experiment.yaml',
                        help='experiment config the results were produced with')
    parser.add_argument('--out', default=None,
                        help='output directory (default: output_dir from the config)')
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)
    output_dir = args.out or config.get('output_dir', 'report_site')

    generate_html_site(load_stats(args.results), config, output_dir)


if __name__ == '__main__':
    main()
