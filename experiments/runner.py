import random
import yaml
from dataclasses import asdict
from tqdm import tqdm

from dubito.core_game import dubito
from dubito.player import Player
from bots.manual import rule_based, probability
from bots.llms import claude as claude_bots, chatgpt as chatgpt_bots, gemini as gemini_bots

from .stats import BotStats, BucketStats, make_bot_stats, hard_win_rate, soft_win_rate, safe_div


ALL_BOTS = {
    'AlwaysTruthful':   rule_based.AlwaysTruthful,
    'JustPutCards':     rule_based.JustPutCards,
    'MrDoubt':          rule_based.MrDoubt,
    'MrNoDoubt':        rule_based.MrNoDoubt,
    'RandomBoi':        rule_based.RandomBoi,
    'StefaBot':         rule_based.StefaBot,
    'AdaptyBoi':        probability.AdaptyBoi,
    'SusBoi':           probability.SusBoi,
    'UsualBot':         probability.UsualBot,
    'RiskCounter':      probability.RiskCounter,
    'ClaudeBot':        claude_bots.ClaudeBot,
    'ChatGPTBot':       chatgpt_bots.ChatGPTBot,
    'ChatGPT_thinking': chatgpt_bots.ChatGPT_thinking,
    'GeminiBot':        gemini_bots.GeminiBot,
}


def load_config(path: str = 'experiment.yaml') -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def save_stats(stats: dict, path: str) -> None:
    with open(path, 'w') as f:
        yaml.dump({k: asdict(v) for k, v in stats.items()}, f, allow_unicode=True)


def print_summary(final_infos: dict) -> None:
    col = 20

    def _section(title: str, bucket: str, rate_fn):
        header = f"{'Bot':<{col}} {'Games':>8} {'Win%':>8} {'Cards/Turn':>11}"
        sep = '=' * len(header)
        print(f'\n{sep}')
        print(title)
        print(sep)
        print(header)
        print('-' * len(header))
        rows = sorted(
            [
                (
                    rate_fn(info) * 100,
                    bot,
                    info.total.games,
                    safe_div(getattr(info, bucket).cards_played,
                             getattr(info, bucket).play_turns),
                )
                for bot, info in final_infos.items()
                if info.total.games > 0
            ],
            reverse=True,
        )
        for win_pct, bot, total, cards_per_turn in rows:
            print(f"{bot:<{col}} {total:>8} {win_pct:>7.1f}% {cards_per_turn:>11.2f}")
        print(sep)

    _section('Hard Wins (1st place)',  'hard_wins', hard_win_rate)
    _section('Soft Wins (2nd to n-1)', 'soft_wins', soft_win_rate)


def play_games(algorithms: list, available_players: list, n_experiments: int) -> dict:
    players_alg = {a.__name__ for a in algorithms}
    final_infos: dict[str, BotStats] = {alg: make_bot_stats(players_alg) for alg in players_alg}

    for _ in tqdm(range(n_experiments), desc='Playing Games', unit='game'):
        player_number = random.choice(available_players)
        all_players: list[Player] = [
            random.choice(algorithms)(i)
            for i in range(1, player_number + 1)
        ]

        results, game_infos = dubito(all_players)
        stats = game_infos['stats'].data
        n = len(all_players)
        winners = results['winners']
        n_winners = len(winners)

        for idx, p in enumerate(all_players):
            name = p.__class__.__name__
            if winners and p is winners[0]:
                outcome = 'hard_wins'
            elif p in winners:
                outcome = 'soft_wins'
            else:
                outcome = 'losses'
            prev_name = all_players[(idx - 1) % n].__class__.__name__
            next_name = all_players[(idx + 1) % n].__class__.__name__
            s = stats[p.id]

            if p in winners:
                raw_pos = winners.index(p) + 1
            else:
                raw_pos = n_winners + 1
            rel_pos = (n - raw_pos) / (n - 1) if n > 1 else 0.5

            for bucket in ('total', outcome):
                b: BucketStats = getattr(final_infos[name], bucket)
                b.games += 1
                b.prev[prev_name] += 1
                b.next[next_name] += 1
                b.avg_cards += len(p.cards)
                b.bluffs += s['bluffs']
                b.bluff_caught += s['dishonest_times']
                b.doubts += s['doubts']
                b.successful_doubts += s['successful_doubts']
                b.cards_played += s['total_cards_played']
                b.play_turns += s['play_turns']
                b.not_first_turns += s['not_first_turns']
                b.total_position += rel_pos

    for alg in players_alg:
        for bucket in ('total', 'hard_wins', 'soft_wins', 'losses'):
            b: BucketStats = getattr(final_infos[alg], bucket)
            if b.games > 0:
                b.avg_cards /= b.games
                b.total_position /= b.games

    return final_infos
