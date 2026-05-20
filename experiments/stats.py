from dataclasses import dataclass, field


@dataclass
class BucketStats:
    games: int = 0
    prev: dict = field(default_factory=dict)   # {bot_name: game_count}
    next: dict = field(default_factory=dict)   # {bot_name: game_count}
    avg_cards: float = 0.0
    bluffs: int = 0
    bluff_caught: int = 0
    doubts: int = 0
    successful_doubts: int = 0
    cards_played: int = 0
    play_turns: int = 0
    not_first_turns: int = 0
    total_position: float = 0.0


@dataclass
class BotStats:
    total:     BucketStats = field(default_factory=BucketStats)
    hard_wins: BucketStats = field(default_factory=BucketStats)  # finished 1st
    soft_wins: BucketStats = field(default_factory=BucketStats)  # finished 2nd to n-1
    losses:    BucketStats = field(default_factory=BucketStats)  # finished last


def make_bot_stats(players_alg: set) -> BotStats:
    def _bucket():
        return BucketStats(
            prev={alg: 0 for alg in players_alg},
            next={alg: 0 for alg in players_alg},
        )
    return BotStats(total=_bucket(), hard_wins=_bucket(), soft_wins=_bucket(), losses=_bucket())


def safe_div(num: float, den: float, fallback: float = 0.0) -> float:
    return num / den if den > 0 else fallback


def win_rate(info: BotStats) -> float:
    """Combined win rate: any finish that is not last (hard + soft)."""
    total = info.total.games
    return (info.hard_wins.games + info.soft_wins.games) / total if total > 0 else 0.0


def hard_win_rate(info: BotStats) -> float:
    return info.hard_wins.games / info.total.games if info.total.games > 0 else 0.0


def soft_win_rate(info: BotStats) -> float:
    return info.soft_wins.games / info.total.games if info.total.games > 0 else 0.0
