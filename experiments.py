from dubito.core_game import dubito
from dubito.player import Player
from tqdm import tqdm
import random
import yaml
import copy
import sys
import datetime
from bots.manual import rule_based, probability
from bots.llms import claude as claude_bots, chatgpt as chatgpt_bots, gemini as gemini_bots


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
    'ClaudeBot':      claude_bots.ClaudeBot,
    'ChatGPTBot':     chatgpt_bots.ChatGPTBot,
    'ChatGPT_thinking': chatgpt_bots.ChatGPT_thinking,
    'GeminiBot':      gemini_bots.GeminiBot,
}


def load_config(path: str = 'experiment.yaml') -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def save_stats(stats: dict, path: str) -> None:
    with open(path, 'w') as f:
        yaml.dump(stats, f, allow_unicode=True)


def print_summary(final_infos: dict) -> None:
    col = 20
    sep_len = col + 8 + 9 + 9 + 11

    def _section(title: str, bucket: str, rate_fn):
        header = f"{'Bot':<{col}} {'Games':>8} {'Win%':>8} {'Avg Cards':>10}"
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
                    info['total']['games'],
                    info[bucket]['avg_cards'],
                )
                for bot, info in final_infos.items()
                if info['total']['games'] > 0
            ],
            reverse=True,
        )
        for win_pct, bot, total, avg_cards in rows:
            print(f"{bot:<{col}} {total:>8} {win_pct:>7.1f}% {avg_cards:>10.2f}")
        print(sep)

    _section('Hard Wins (1st place)',    'hard_wins', _hard_win_rate)
    _section('Soft Wins (2nd to n-1)',   'soft_wins', _soft_win_rate)


def play_games(algorithms: list, available_players: list[int], n_experiments: int) -> dict:
    players_alg = {a.__name__ for a in algorithms}

    placeholder = {
        'games': 0,
        'prev': {alg: 0 for alg in players_alg},
        'next': {alg: 0 for alg in players_alg},
        'avg_cards': 0.0,
        # per-turn behaviour counters
        'bluffs': 0,
        'bluff_caught': 0,
        'doubts': 0,
        'successful_doubts': 0,
        'cards_played': 0,
        'play_turns': 0,
        'not_first_turns': 0,
        # relative finish position: 1.0 = 1st, 0.0 = last (normalized across n players)
        'total_position': 0.0,
    }

    final_infos = {
        alg: {
            'total':      copy.deepcopy(placeholder),
            'hard_wins':  copy.deepcopy(placeholder),  # finished 1st
            'soft_wins':  copy.deepcopy(placeholder),  # finished 2nd to n-1
            'losses':     copy.deepcopy(placeholder),  # finished last
        }
        for alg in players_alg
    }

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

            # Relative finish position: 1.0 = 1st place, 0.0 = last place
            if p in winners:
                raw_pos = winners.index(p) + 1
            else:
                raw_pos = n_winners + 1  # tied for last
            rel_pos = (n - raw_pos) / (n - 1) if n > 1 else 0.5

            for bucket in ('total', outcome):
                b = final_infos[name][bucket]
                b['games'] += 1
                b['prev'][prev_name] += 1
                b['next'][next_name] += 1
                b['avg_cards'] += len(p.cards)
                b['bluffs'] += s['bluffs']
                b['bluff_caught'] += s['dishonest_times']
                b['doubts'] += s['doubts']
                b['successful_doubts'] += s['successful_doubts']
                b['cards_played'] += s['total_cards_played']
                b['play_turns'] += s['play_turns']
                b['not_first_turns'] += s['not_first_turns']
                b['total_position'] += rel_pos

    for alg in players_alg:
        for bucket in ('total', 'hard_wins', 'soft_wins', 'losses'):
            g = final_infos[alg][bucket]['games']
            if g > 0:
                final_infos[alg][bucket]['avg_cards'] /= g
                final_infos[alg][bucket]['total_position'] /= g

    return final_infos


# ── HTML report ────────────────────────────────────────────────────────────────

def _win_rate(info: dict) -> float:
    """Combined win rate: any finish that is not last (hard + soft)."""
    total = info['total']['games']
    wins  = info['hard_wins']['games'] + info['soft_wins']['games']
    return wins / total if total > 0 else 0.0

def _hard_win_rate(info: dict) -> float:
    total = info['total']['games']
    return info['hard_wins']['games'] / total if total > 0 else 0.0

def _soft_win_rate(info: dict) -> float:
    total = info['total']['games']
    return info['soft_wins']['games'] / total if total > 0 else 0.0


def _safe(num, den, fallback=0.0) -> float:
    return num / den if den > 0 else fallback


def _neighbor_win_rates(bot: str, data: dict, position: str) -> dict[str, float]:
    """Win rate of `bot` for each possible neighbor at `position` (prev/next)."""
    rates = {}
    for neighbor in data[bot]['total'][position]:
        if neighbor == bot:
            continue
        wins  = (data[bot]['hard_wins'][position].get(neighbor, 0)
                 + data[bot]['soft_wins'][position].get(neighbor, 0))
        total = data[bot]['total'][position].get(neighbor, 0)
        if total > 0:
            rates[neighbor] = wins / total
    return rates


def _build_heatmap_matrix(data: dict, players: list[str], position: str):
    import numpy as np
    n = len(players)
    matrix = [[None] * n for _ in range(n)]
    text   = [[''] * n for _ in range(n)]
    for i, current in enumerate(players):
        for j, neighbour in enumerate(players):
            wins  = (data[current]['hard_wins'][position].get(neighbour, 0)
                     + data[current]['soft_wins'][position].get(neighbour, 0))
            total = data[current]['total'][position].get(neighbour, 0)
            if total > 0:
                v = wins / total
                matrix[i][j] = round(v, 3)
                text[i][j]   = f'{v:.2f}'
    return matrix, text


def _compute_bot_metrics(bot: str, final_infos: dict) -> dict:
    """Centralised derived stats for a bot (used by radar, scatter, position charts)."""
    info = final_infos[bot]
    t    = info['total']
    return {
        'win_rate':       _win_rate(info),
        'hard_win_rate':  _hard_win_rate(info),
        'soft_win_rate':  _soft_win_rate(info),
        'avg_position':   t['total_position'],   # 1.0 = always 1st, 0.0 = always last
        'bluff_rate':     _safe(t['bluffs'], t['play_turns']),
        'bluff_stealth':  _safe(t['bluffs'] - t['bluff_caught'], t['bluffs']),
        'doubt_rate':     _safe(t['doubts'], t['not_first_turns']),
        'doubt_accuracy': _safe(t['successful_doubts'], t['doubts']),
        'cards_per_turn': _safe(t['cards_played'], t['play_turns']),
    }


def generate_html_report(final_infos: dict, config: dict, output_path: str = 'report.html') -> None:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    players = sorted(final_infos.keys(), key=lambda b: _win_rate(final_infos[b]), reverse=True)
    n_bots  = len(players)
    baseline = 1.0 / n_bots

    # ── colour palette (one colour per bot, consistent everywhere) ─────────────
    palette = [
        '#4C78A8', '#F58518', '#E45756', '#72B7B2', '#54A24B',
        '#EECA3B', '#B279A2', '#FF9DA7', '#9D755D', '#BAB0AC',
        '#FF7F0E', '#2CA02C', '#D62728', '#9467BD',
    ]
    bot_colour = {b: palette[i % len(palette)] for i, b in enumerate(players)}

    win_rates   = [_win_rate(final_infos[b]) for b in players]
    total_games = [final_infos[b]['total']['games'] for b in players]
    win_games   = [final_infos[b]['wins']['games']  for b in players]
    avg_total   = [final_infos[b]['total']['avg_cards'] for b in players]
    avg_wins    = [final_infos[b]['wins']['avg_cards']  for b in players]
    avg_losses  = [final_infos[b]['losses']['avg_cards'] for b in players]

    # ── chart 1: win rate bar ──────────────────────────────────────────────────
    fig_wr = go.Figure()
    fig_wr.add_trace(go.Bar(
        x=players, y=win_rates,
        marker_color=[bot_colour[b] for b in players],
        text=[f'{v:.1%}' for v in win_rates],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Win rate: %{y:.2%}<extra></extra>',
    ))
    fig_wr.add_hline(y=baseline, line_dash='dot', line_color='crimson',
                     annotation_text=f'Baseline ({baseline:.1%})',
                     annotation_position='top right')
    fig_wr.update_layout(
        title='Win Rate by Bot', yaxis_title='Win Rate',
        yaxis_tickformat='.0%', yaxis_range=[0, max(win_rates) * 1.15],
        plot_bgcolor='white', paper_bgcolor='white',
        font_family='Inter, sans-serif',
        margin=dict(t=60, b=80),
    )
    fig_wr.update_xaxes(tickangle=-35)

    # ── chart 2: avg cards grouped bar ────────────────────────────────────────
    fig_cards = go.Figure()
    for label, vals, opacity in [('Total', avg_total, 1.0), ('On wins', avg_wins, 0.75), ('On losses', avg_losses, 0.5)]:
        fig_cards.add_trace(go.Bar(
            name=label, x=players, y=vals,
            marker_color=[bot_colour[b] for b in players],
            marker_opacity=opacity,
            text=[f'{v:.2f}' for v in vals],
            textposition='outside',
            hovertemplate=f'<b>%{{x}}</b><br>{label}: %{{y:.2f}} cards<extra></extra>',
        ))
    fig_cards.update_layout(
        barmode='group', title='Average Cards in Hand',
        yaxis_title='Avg cards',
        plot_bgcolor='white', paper_bgcolor='white',
        font_family='Inter, sans-serif',
        margin=dict(t=60, b=80),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    fig_cards.update_xaxes(tickangle=-35)

    # ── chart 3 & 4: heatmaps ─────────────────────────────────────────────────
    def _heatmap_fig(position: str, title: str) -> go.Figure:
        matrix, text = _build_heatmap_matrix(final_infos, players, position)
        fig = go.Figure(go.Heatmap(
            z=matrix, x=players, y=players,
            text=text, texttemplate='%{text}',
            colorscale='RdYlGn', zmin=0, zmax=1,
            colorbar=dict(title='Win rate'),
            hovertemplate=f'<b>%{{y}}</b> vs <b>%{{x}}</b> as {position}<br>Win rate: %{{z:.2f}}<extra></extra>',
        ))
        fig.update_layout(
            title=title,
            xaxis_title=f'{position.capitalize()} player',
            yaxis_title='Current player',
            plot_bgcolor='white', paper_bgcolor='white',
            font_family='Inter, sans-serif',
            margin=dict(t=60, b=100, l=100),
        )
        fig.update_xaxes(tickangle=-45)
        return fig

    fig_hm_prev = _heatmap_fig('prev', 'Win Rate given Prev Neighbor')
    fig_hm_next = _heatmap_fig('next', 'Win Rate given Next Neighbor')

    # ── pre-compute all derived metrics ───────────────────────────────────────
    metrics = {b: _compute_bot_metrics(b, final_infos) for b in players}

    # ── chart 5: radar / spider chart ─────────────────────────────────────────
    axes_raw = {}
    for b in players:
        m = metrics[b]
        axes_raw[b] = {
            'Win Rate':       m['win_rate'],
            'Bluff Rate':     m['bluff_rate'],
            'Bluff Stealth':  m['bluff_stealth'],
            'Doubt Rate':     m['doubt_rate'],
            'Doubt Accuracy': m['doubt_accuracy'],
            'Cards per Turn': m['cards_per_turn'],
        }

    # Normalize "Cards per Turn" to [0,1] so all axes share the same scale.
    max_cpt = max((axes_raw[b]['Cards per Turn'] for b in players), default=1) or 1
    for b in players:
        axes_raw[b]['Cards per Turn'] /= max_cpt

    axis_labels = ['Win Rate', 'Bluff Rate', 'Bluff Stealth',
                   'Doubt Rate', 'Doubt Accuracy', 'Cards per Turn']
    axis_labels_closed = axis_labels + [axis_labels[0]]  # close the polygon

    fig_radar = go.Figure()
    for bot in players:
        vals = [axes_raw[bot][a] for a in axis_labels]
        vals_closed = vals + [vals[0]]
        fig_radar.add_trace(go.Scatterpolar(
            r=vals_closed,
            theta=axis_labels_closed,
            name=bot,
            line_color=bot_colour[bot],
            fill='toself',
            fillcolor=bot_colour[bot],
            opacity=0.15,
            hovertemplate=(
                f'<b>{bot}</b><br>'
                + '<br>'.join(f'{a}: %{{r[{i}]:.2f}}' for i, a in enumerate(axis_labels))
                + '<extra></extra>'
            ),
        ))
    fig_radar.update_layout(
        title='Bot Behaviour Radar (click legend to toggle)',
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], tickformat='.0%'),
            angularaxis=dict(tickfont=dict(size=12)),
        ),
        showlegend=True,
        legend=dict(orientation='v', x=1.05, y=0.5),
        plot_bgcolor='white', paper_bgcolor='white',
        font_family='Inter, sans-serif',
        margin=dict(t=60, b=40, l=60, r=180),
        height=560,
    )

    # ── chart 6: avg relative position ────────────────────────────────────────
    pos_bots   = sorted(players, key=lambda b: metrics[b]['avg_position'], reverse=True)
    pos_vals   = [metrics[b]['avg_position'] for b in pos_bots]
    fig_pos = go.Figure()
    fig_pos.add_trace(go.Bar(
        x=pos_bots, y=pos_vals,
        marker_color=[bot_colour[b] for b in pos_bots],
        text=[f'{v:.2f}' for v in pos_vals],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Avg relative position: %{y:.3f}<extra></extra>',
    ))
    fig_pos.add_hline(y=0.5, line_dash='dot', line_color='crimson',
                      annotation_text='Random baseline (0.5)',
                      annotation_position='top right')
    fig_pos.update_layout(
        title='Avg Relative Finish Position (1.0 = always 1st, 0.0 = always last)',
        yaxis_title='Relative position', yaxis_range=[0, 1.15],
        plot_bgcolor='white', paper_bgcolor='white',
        font_family='Inter, sans-serif', margin=dict(t=60, b=80),
    )
    fig_pos.update_xaxes(tickangle=-35)

    # ── helper: build a labelled scatter plot ─────────────────────────────────
    def _scatter(x_key: str, y_key: str, x_label: str, y_label: str, title: str) -> go.Figure:
        fig = go.Figure()
        for b in players:
            m = metrics[b]
            fig.add_trace(go.Scatter(
                x=[m[x_key]], y=[m[y_key]],
                mode='markers+text',
                name=b,
                text=[b],
                textposition='top center',
                marker=dict(color=bot_colour[b], size=12),
                hovertemplate=f'<b>{b}</b><br>{x_label}: %{{x:.2f}}<br>{y_label}: %{{y:.2f}}<extra></extra>',
                showlegend=False,
            ))
        fig.update_layout(
            title=title,
            xaxis_title=x_label, yaxis_title=y_label,
            plot_bgcolor='white', paper_bgcolor='white',
            font_family='Inter, sans-serif',
            margin=dict(t=60, b=60),
            height=420,
        )
        return fig

    fig_sc_style   = _scatter('bluff_rate',    'doubt_rate',     'Bluff Rate',    'Doubt Rate',    'Style Space: Bluff Rate vs Doubt Rate')
    fig_sc_agg_wr  = _scatter('bluff_rate',    'win_rate',       'Bluff Rate',    'Win Rate',      'Does Aggression Pay Off? Bluff Rate vs Win Rate')
    fig_sc_quality = _scatter('bluff_stealth', 'doubt_accuracy', 'Bluff Stealth', 'Doubt Accuracy','Deception Quality: Bluff Stealth vs Doubt Accuracy')
    fig_sc_pos_wr  = _scatter('avg_position',  'win_rate',       'Avg Relative Position', 'Win Rate', 'Position vs Win Rate')

    # ── per-bot neighbor charts ────────────────────────────────────────────────
    def _neighbor_fig(bot: str, position: str) -> go.Figure:
        rates = _neighbor_win_rates(bot, final_infos, position)
        nbrs  = sorted(rates, key=lambda x: rates[x], reverse=True)
        vals  = [rates[n] for n in nbrs]
        colours = [bot_colour.get(n, '#888') for n in nbrs]
        fig = go.Figure(go.Bar(
            x=nbrs, y=vals,
            marker_color=colours,
            text=[f'{v:.1%}' for v in vals],
            textposition='outside',
            hovertemplate=f'<b>%{{x}}</b> as {position} neighbor<br>Win rate: %{{y:.2%}}<extra></extra>',
        ))
        fig.add_hline(y=0.5, line_dash='dot', line_color='grey')
        fig.update_layout(
            title=f'{position.capitalize()} neighbor',
            yaxis_title='Win rate', yaxis_tickformat='.0%',
            yaxis_range=[0, max(vals, default=0.5) * 1.2 + 0.05],
            plot_bgcolor='white', paper_bgcolor='white',
            font_family='Inter, sans-serif',
            margin=dict(t=50, b=70),
            height=300,
        )
        fig.update_xaxes(tickangle=-35)
        return fig

    # ── helpers to turn figures into embeddable divs ───────────────────────────
    def _div(fig: go.Figure, div_id: str = '', height: str = '420px') -> str:
        kwargs = dict(full_html=False, include_plotlyjs=False, config={'responsive': True})
        if div_id:
            kwargs['div_id'] = div_id
        html = fig.to_html(**kwargs)
        # wrap in a sized container
        return f'<div style="width:100%;height:{height};">{html}</div>'

    # ── baselines (approximate, from config player range) ─────────────────────
    ap          = config.get('available_players', [5])
    avg_n       = sum(ap) / len(ap)
    hard_base   = 1.0 / avg_n
    soft_base   = max(0.0, (avg_n - 2) / avg_n)

    # ── hard-win table rows (sorted by hard win rate) ──────────────────────────
    hard_rows = ''
    for rank, bot in enumerate(sorted(players, key=lambda b: _hard_win_rate(final_infos[b]), reverse=True), 1):
        info   = final_infos[bot]
        hwr    = _hard_win_rate(info)
        colour = bot_colour[bot]
        badge  = f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{colour};margin-right:6px;"></span>'
        hard_rows += f'''
        <tr>
          <td class="text-center text-muted">{rank}</td>
          <td><a href="#{bot}" class="text-decoration-none fw-semibold">{badge}{bot}</a></td>
          <td class="text-end">{info["total"]["games"]:,}</td>
          <td class="text-end">{info["hard_wins"]["games"]:,}</td>
          <td class="text-end fw-bold" style="color:{colour}">{hwr:.1%}</td>
          <td class="text-end">{info["hard_wins"]["avg_cards"]:.2f}</td>
          <td class="text-end" style="color:{'#198754' if hwr >= hard_base else '#dc3545'};">{(hwr - hard_base):+.1%}</td>
          <td class="text-end text-danger">{info["losses"]["avg_cards"]:.2f}</td>
        </tr>'''

    # ── soft-win table rows (sorted by soft win rate) ──────────────────────────
    soft_rows = ''
    for rank, bot in enumerate(sorted(players, key=lambda b: _soft_win_rate(final_infos[b]), reverse=True), 1):
        info   = final_infos[bot]
        swr    = _soft_win_rate(info)
        colour = bot_colour[bot]
        badge  = f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{colour};margin-right:6px;"></span>'
        soft_rows += f'''
        <tr>
          <td class="text-center text-muted">{rank}</td>
          <td><a href="#{bot}" class="text-decoration-none fw-semibold">{badge}{bot}</a></td>
          <td class="text-end">{info["total"]["games"]:,}</td>
          <td class="text-end">{info["soft_wins"]["games"]:,}</td>
          <td class="text-end fw-bold" style="color:{colour}">{swr:.1%}</td>
          <td class="text-end">{info["soft_wins"]["avg_cards"]:.2f}</td>
          <td class="text-end" style="color:{'#198754' if swr >= soft_base else '#dc3545'};">{(swr - soft_base):+.1%}</td>
          <td class="text-end text-danger">{info["losses"]["avg_cards"]:.2f}</td>
        </tr>'''

    # ── per-bot section HTML ───────────────────────────────────────────────────
    bot_sections = ''
    for bot in players:
        info   = final_infos[bot]
        hwr    = _hard_win_rate(info)
        swr    = _soft_win_rate(info)
        colour = bot_colour[bot]
        rank   = players.index(bot) + 1
        prev_div = _div(_neighbor_fig(bot, 'prev'), height='320px')
        next_div = _div(_neighbor_fig(bot, 'next'), height='320px')

        bot_sections += f'''
    <div class="card mb-4 shadow-sm" id="{bot}">
      <div class="card-header d-flex align-items-center gap-2" style="background:{colour}20;border-left:4px solid {colour};">
        <span style="font-size:1.1rem;font-weight:700;color:{colour};">#{rank}</span>
        <h5 class="mb-0 ms-1">{bot}</h5>
        <span class="ms-auto badge" style="background:{colour};font-size:0.95rem;">{hwr:.1%} hard win</span>
        <span class="badge bg-secondary">{swr:.1%} soft win</span>
      </div>
      <div class="card-body">
        <div class="row g-3 mb-3">
          <div class="col-6 col-md-2">
            <div class="stat-card">
              <div class="stat-value">{info["total"]["games"]:,}</div>
              <div class="stat-label">Total games</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="stat-card">
              <div class="stat-value" style="color:{colour};">{hwr:.1%}</div>
              <div class="stat-label">Hard Win % (1st)</div>
              <div class="progress mt-1" style="height:4px;">
                <div class="progress-bar" style="width:{int(hwr*100)}%;background:{colour};"></div>
              </div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="stat-card">
              <div class="stat-value" style="color:{'#198754' if hwr >= hard_base else '#dc3545'};">{(hwr - hard_base):+.1%}</div>
              <div class="stat-label">vs Hard Baseline</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="stat-card">
              <div class="stat-value text-secondary">{swr:.1%}</div>
              <div class="stat-label">Soft Win % (2nd+)</div>
              <div class="progress mt-1" style="height:4px;">
                <div class="progress-bar bg-secondary" style="width:{int(swr*100)}%;"></div>
              </div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="stat-card">
              <div class="stat-value" style="color:{'#198754' if swr >= soft_base else '#dc3545'};">{(swr - soft_base):+.1%}</div>
              <div class="stat-label">vs Soft Baseline</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="stat-card">
              <div class="stat-value text-danger">{info["losses"]["avg_cards"]:.2f}</div>
              <div class="stat-label">Avg cards on loss</div>
            </div>
          </div>
        </div>
        <div class="row g-3">
          <div class="col-md-6">{prev_div}</div>
          <div class="col-md-6">{next_div}</div>
        </div>
      </div>
    </div>'''

    # ── experiment config string ───────────────────────────────────────────────
    n_exp     = config.get('n_experiments', '?')
    ap_str    = f'{ap[0]}–{ap[-1]}' if ap else '?'
    generated = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

    # ── assemble full HTML ─────────────────────────────────────────────────────
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Dubito Experiment Report</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet"/>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    body {{ font-family: "Inter", system-ui, sans-serif; background:#f8f9fa; }}
    .navbar-brand {{ font-weight: 700; letter-spacing: .5px; }}
    section {{ scroll-margin-top: 70px; }}
    .stat-card {{
      background: #fff;
      border: 1px solid #e9ecef;
      border-radius: 8px;
      padding: 12px 16px;
      text-align: center;
    }}
    .stat-value {{ font-size: 1.4rem; font-weight: 700; }}
    .stat-label {{ font-size: .75rem; color: #6c757d; text-transform: uppercase; letter-spacing: .5px; }}
    .chart-card {{
      background: #fff;
      border: 1px solid #e9ecef;
      border-radius: 10px;
      padding: 16px;
    }}
    table thead th {{ background: #343a40; color: #fff; white-space: nowrap; }}
    .section-title {{
      font-size: 1.4rem; font-weight: 700;
      border-left: 4px solid #4C78A8;
      padding-left: 12px;
      margin-bottom: 1rem;
    }}
    .config-badge {{
      display: inline-block;
      background: #e9ecef;
      border-radius: 20px;
      padding: 4px 14px;
      font-size: .85rem;
      font-weight: 600;
      margin: 2px;
    }}
    a[href^="#"] {{ color: inherit; }}
  </style>
</head>
<body>

<!-- Navbar -->
<nav class="navbar navbar-dark bg-dark sticky-top px-4">
  <span class="navbar-brand">🎴 Dubito Experiment Report</span>
  <span class="text-white-50 small">Generated {generated}</span>
</nav>

<div class="container-lg py-4">

  <!-- Config banner -->
  <div class="alert alert-dark mb-4">
    <strong>Experiment config:</strong>&nbsp;
    <span class="config-badge">🎲 {n_exp:,} games</span>
    <span class="config-badge">👥 {ap_str} players/game</span>
    <span class="config-badge">🤖 {n_bots} bots</span>
  </div>

  <!-- Overview tables -->
  <section id="overview" class="mb-5">
    <div class="section-title">Hard Wins — 1st Place</div>
    <p class="text-muted small mb-2">A <strong>hard win</strong> means the bot was the first to empty their hand.
      Baseline ≈ {hard_base:.1%} (1 / avg players).</p>
    <div class="table-responsive mb-5">
      <table class="table table-hover table-bordered align-middle mb-0 bg-white shadow-sm">
        <thead>
          <tr>
            <th class="text-center">#</th>
            <th>Bot</th>
            <th class="text-end">Total games</th>
            <th class="text-end">Hard Wins</th>
            <th class="text-end">Hard Win %</th>
            <th class="text-end">Avg cards (hard win)</th>
            <th class="text-end">vs Baseline</th>
            <th class="text-end">Avg cards on loss</th>
          </tr>
        </thead>
        <tbody>{hard_rows}</tbody>
      </table>
    </div>

    <div class="section-title">Soft Wins — 2nd to n−1</div>
    <p class="text-muted small mb-2">A <strong>soft win</strong> means the bot finished above last but did not finish 1st.
      Baseline ≈ {soft_base:.1%} ((avg players − 2) / avg players).</p>
    <div class="table-responsive">
      <table class="table table-hover table-bordered align-middle mb-0 bg-white shadow-sm">
        <thead>
          <tr>
            <th class="text-center">#</th>
            <th>Bot</th>
            <th class="text-end">Total games</th>
            <th class="text-end">Soft Wins</th>
            <th class="text-end">Soft Win %</th>
            <th class="text-end">Avg cards (soft win)</th>
            <th class="text-end">vs Baseline</th>
            <th class="text-end">Avg cards on loss</th>
          </tr>
        </thead>
        <tbody>{soft_rows}</tbody>
      </table>
    </div>
  </section>

  <!-- Global charts -->
  <section id="global" class="mb-5">
    <div class="section-title">Global Charts</div>
    <div class="row g-4">
      <div class="col-12">
        <div class="chart-card">{_div(fig_wr, height='440px')}</div>
      </div>
      <div class="col-12">
        <div class="chart-card">{_div(fig_cards, height='440px')}</div>
      </div>
      <div class="col-12 col-xl-6">
        <div class="chart-card">{_div(fig_hm_prev, height='520px')}</div>
      </div>
      <div class="col-12 col-xl-6">
        <div class="chart-card">{_div(fig_hm_next, height='520px')}</div>
      </div>
      <div class="col-12">
        <div class="chart-card">{_div(fig_pos, height='440px')}</div>
      </div>
      <div class="col-12">
        <div class="chart-card">
          {_div(fig_radar, height='580px')}
          <p class="text-muted small mt-1 mb-0 text-center">
            All axes normalized to [0–1].
            <b>Bluff Rate</b>: dishonest plays / total play turns.
            <b>Bluff Stealth</b>: uncaught bluffs / total bluffs.
            <b>Doubt Rate</b>: doubts / eligible turns.
            <b>Doubt Accuracy</b>: successful doubts / total doubts.
            <b>Cards per Turn</b>: avg cards placed per play turn (normalized by max).
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- Scatter analysis -->
  <section id="scatter" class="mb-5">
    <div class="section-title">Style &amp; Strategy Analysis</div>
    <div class="row g-4">
      <div class="col-12 col-xl-6">
        <div class="chart-card">{_div(fig_sc_style,   height='440px')}</div>
      </div>
      <div class="col-12 col-xl-6">
        <div class="chart-card">{_div(fig_sc_agg_wr,  height='440px')}</div>
      </div>
      <div class="col-12 col-xl-6">
        <div class="chart-card">{_div(fig_sc_quality, height='440px')}</div>
      </div>
      <div class="col-12 col-xl-6">
        <div class="chart-card">{_div(fig_sc_pos_wr,  height='440px')}</div>
      </div>
    </div>
  </section>

  <!-- Per-bot sections -->
  <section id="bots" class="mb-5">
    <div class="section-title">Per-Bot Breakdown</div>
    {bot_sections}
  </section>

</div>

<footer class="text-center text-muted py-3 border-top small">
  Dubito Experiment Report &mdash; {generated}
</footer>

</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'HTML report saved to {output_path}')


# ── entry point ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'experiment.yaml'
    config = load_config(config_path)

    bot_names = config.get('bots', list(ALL_BOTS.keys()))
    algorithms = [ALL_BOTS[name] for name in bot_names]
    available_players = config['available_players']
    n_experiments = config['n_experiments']
    output_file = config.get('output_file', 'all_games.yaml')
    output_html = config.get('output_html', 'report.html')

    print(f"Running {n_experiments:,} games with {len(algorithms)} bots "
          f"and {available_players[0]}–{available_players[-1]} players per game.")

    final_infos = play_games(algorithms, available_players, n_experiments)

    save_stats(final_infos, output_file)
    print(f"\nResults saved to {output_file}")

    print_summary(final_infos)

    print('\nGenerating HTML report...')
    generate_html_report(final_infos, config, output_html)
