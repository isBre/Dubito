from plotly import graph_objects as go

from ..stats import safe_div
from ._common import LAYOUT_BASE


# ── Overview ──────────────────────────────────────────────────────────────────

def win_type_scatter(players, metrics, bot_colour, hard_base, soft_base) -> go.Figure:
    fig = go.Figure()
    for b in players:
        m = metrics[b]
        fig.add_trace(go.Scatter(
            x=[m['hard_win_rate']], y=[m['soft_win_rate']],
            mode='markers+text', name=b, text=[b], textposition='top center',
            marker=dict(color=bot_colour[b], size=14),
            hovertemplate=f'<b>{b}</b><br>Hard Win: %{{x:.1%}}<br>Soft Win: %{{y:.1%}}<extra></extra>',
            showlegend=False,
        ))
    fig.add_vline(x=hard_base, line_dash='dot', line_color='crimson',
                  annotation_text=f'Hard baseline ({hard_base:.1%})', annotation_position='top right')
    fig.add_hline(y=soft_base, line_dash='dot', line_color='steelblue',
                  annotation_text=f'Soft baseline ({soft_base:.1%})', annotation_position='top left')
    fig.update_layout(
        title='Win-Type Space: Hard Win % vs Soft Win %',
        xaxis_title='Hard Win % (1st place)', yaxis_title='Soft Win % (2nd–n−2)',
        xaxis_tickformat='.0%', yaxis_tickformat='.0%',
        **LAYOUT_BASE, margin=dict(t=60, b=60), height=460,
    )
    return fig


# ── Rankings ──────────────────────────────────────────────────────────────────

def win_rate_bar(players, metrics, bot_colour, win_base) -> go.Figure:
    win_rates = [metrics[b]['win_rate'] for b in players]
    fig = go.Figure(go.Bar(
        x=players, y=win_rates,
        marker_color=[bot_colour[b] for b in players],
        text=[f'{v:.1%}' for v in win_rates], textposition='outside',
        hovertemplate='<b>%{x}</b><br>Win rate: %{y:.2%}<extra></extra>',
    ))
    fig.add_hline(y=win_base, line_dash='dot', line_color='crimson',
                  annotation_text=f'Baseline ({win_base:.1%})', annotation_position='top right')
    fig.update_layout(
        title='Overall Win Rate (Hard + Soft Wins)',
        yaxis_title='Win Rate', yaxis_tickformat='.0%',
        yaxis_range=[0, max(win_rates) * 1.15],
        **LAYOUT_BASE, margin=dict(t=60, b=80),
    )
    fig.update_xaxes(tickangle=-35)
    return fig


def outcome_composition(players, metrics) -> go.Figure:
    fig = go.Figure()
    for label, key, color in [
        ('Hard Win (1st)', 'hard_win_rate', '#198754'),
        ('Soft Win (2nd+)', 'soft_win_rate', '#0d6efd'),
        ('Loss (last)', 'loss_rate', '#dc3545'),
    ]:
        vals = [metrics[b][key] for b in players]
        fig.add_trace(go.Bar(
            name=label, x=players, y=vals, marker_color=color,
            text=[f'{v:.1%}' for v in vals],
            textposition='inside', insidetextanchor='middle',
            hovertemplate=f'<b>%{{x}}</b><br>{label}: %{{y:.2%}}<extra></extra>',
        ))
    fig.update_layout(
        barmode='stack', title='Outcome Composition per Bot',
        yaxis_title='Fraction of games', yaxis_tickformat='.0%',
        **LAYOUT_BASE, margin=dict(t=60, b=80),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    fig.update_xaxes(tickangle=-35)
    return fig


def avg_position(players, metrics, bot_colour) -> go.Figure:
    pos_bots = sorted(players, key=lambda b: metrics[b]['avg_position'], reverse=True)
    pos_vals = [metrics[b]['avg_position'] for b in pos_bots]
    fig = go.Figure(go.Bar(
        x=pos_bots, y=pos_vals,
        marker_color=[bot_colour[b] for b in pos_bots],
        text=[f'{v:.2f}' for v in pos_vals], textposition='outside',
        hovertemplate='<b>%{x}</b><br>Avg relative position: %{y:.3f}<extra></extra>',
    ))
    fig.add_hline(y=0.5, line_dash='dot', line_color='crimson',
                  annotation_text='Random baseline (0.5)', annotation_position='top right')
    fig.update_layout(
        title='Avg Relative Finish Position (1.0 = always 1st, 0.0 = always last)',
        yaxis_title='Relative position', yaxis_range=[0, 1.15],
        **LAYOUT_BASE, margin=dict(t=60, b=80),
    )
    fig.update_xaxes(tickangle=-35)
    return fig


def avg_cards(players, final_infos, bot_colour) -> go.Figure:
    avg_total  = [final_infos[b].total.avg_cards for b in players]
    avg_losses = [final_infos[b].losses.avg_cards for b in players]
    avg_wins = [
        safe_div(
            final_infos[b].hard_wins.avg_cards * final_infos[b].hard_wins.games
            + final_infos[b].soft_wins.avg_cards * final_infos[b].soft_wins.games,
            final_infos[b].hard_wins.games + final_infos[b].soft_wins.games,
        )
        for b in players
    ]
    fig = go.Figure()
    for label, vals, opacity in [
        ('Total', avg_total, 1.0), ('On wins', avg_wins, 0.75), ('On losses', avg_losses, 0.5),
    ]:
        fig.add_trace(go.Bar(
            name=label, x=players, y=vals,
            marker_color=[bot_colour[b] for b in players], marker_opacity=opacity,
            text=[f'{v:.2f}' for v in vals], textposition='outside',
            hovertemplate=f'<b>%{{x}}</b><br>{label}: %{{y:.2f}} cards<extra></extra>',
        ))
    fig.update_layout(
        barmode='group', title='Average Cards in Hand at Game End',
        yaxis_title='Avg cards',
        **LAYOUT_BASE, margin=dict(t=60, b=80),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    fig.update_xaxes(tickangle=-35)
    return fig


# ── Behavioral Profiles ───────────────────────────────────────────────────────

def radar(players, metrics, bot_colour) -> go.Figure:
    axes = ['Win Rate', 'Bluff Rate', 'Bluff Stealth', 'Doubt Rate', 'Doubt Accuracy', 'Cards per Turn']
    keys = ['win_rate', 'bluff_rate', 'bluff_stealth', 'doubt_rate', 'doubt_accuracy', 'cards_per_turn']
    max_cpt = max(metrics[b]['cards_per_turn'] for b in players) or 1
    closed  = axes + [axes[0]]

    fig = go.Figure()
    for b in players:
        m    = metrics[b]
        vals = [m[k] if k != 'cards_per_turn' else m[k] / max_cpt for k in keys]
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=closed, name=b,
            line_color=bot_colour[b], fill='toself',
            fillcolor=bot_colour[b], opacity=0.15,
            hovertemplate=(
                f'<b>{b}</b><br>' +
                '<br>'.join(f'{a}: %{{r[{i}]:.2f}}' for i, a in enumerate(axes)) +
                '<extra></extra>'
            ),
        ))
    fig.update_layout(
        title='Behavioral Fingerprint (click legend to toggle)',
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], tickformat='.0%'),
            angularaxis=dict(tickfont=dict(size=12)),
        ),
        showlegend=True,
        legend=dict(orientation='v', x=1.05, y=0.5),
        **LAYOUT_BASE, margin=dict(t=60, b=40, l=60, r=180), height=560,
    )
    return fig


def parcoords(players, metrics, bot_colour) -> go.Figure:
    n  = len(players)
    cs = [[i / max(n - 1, 1), bot_colour[b]] for i, b in enumerate(players)]
    fig = go.Figure(go.Parcoords(
        line=dict(color=list(range(n)), colorscale=cs, showscale=False),
        dimensions=[
            dict(label='Win Rate',       values=[metrics[b]['win_rate']       for b in players], tickformat='.0%', range=[0, 1]),
            dict(label='Hard Win %',     values=[metrics[b]['hard_win_rate']  for b in players], tickformat='.0%', range=[0, 1]),
            dict(label='Bluff Rate',     values=[metrics[b]['bluff_rate']     for b in players], tickformat='.0%', range=[0, 1]),
            dict(label='Bluff Stealth',  values=[metrics[b]['bluff_stealth']  for b in players], tickformat='.0%', range=[0, 1]),
            dict(label='Doubt Rate',     values=[metrics[b]['doubt_rate']     for b in players], tickformat='.0%', range=[0, 1]),
            dict(label='Doubt Accuracy', values=[metrics[b]['doubt_accuracy'] for b in players], tickformat='.0%', range=[0, 1]),
            dict(label='Cards/Turn',     values=[metrics[b]['cards_per_turn'] for b in players], tickformat='.2f'),
        ],
        labelfont=dict(size=12),
    ))
    fig.update_layout(
        title='Parallel Coordinates — all metrics (drag axis range to filter bots)',
        **LAYOUT_BASE, margin=dict(t=80, b=60, l=80, r=80), height=500,
    )
    return fig


def scatter(x_key, y_key, x_label, y_label, title,
            players, metrics, bot_colour, x_fmt='.1%', y_fmt='.1%') -> go.Figure:
    fig = go.Figure()
    for b in players:
        m = metrics[b]
        fig.add_trace(go.Scatter(
            x=[m[x_key]], y=[m[y_key]], mode='markers+text', name=b,
            text=[b], textposition='top center',
            marker=dict(color=bot_colour[b], size=12),
            hovertemplate=f'<b>{b}</b><br>{x_label}: %{{x:{x_fmt}}}<br>{y_label}: %{{y:{y_fmt}}}<extra></extra>',
            showlegend=False,
        ))
    fig.update_layout(
        title=title, xaxis_title=x_label, yaxis_title=y_label,
        **LAYOUT_BASE, margin=dict(t=60, b=60), height=420,
    )
    return fig


def scatter_highlight(x_key, y_key, x_label, y_label, title,
                       players, metrics, bot_colour, highlight,
                       x_fmt='.1%', y_fmt='.1%') -> go.Figure:
    fig = go.Figure()
    for b in players:
        if b == highlight:
            continue
        m = metrics[b]
        fig.add_trace(go.Scatter(
            x=[m[x_key]], y=[m[y_key]], mode='markers+text', name=b,
            text=[b], textposition='top center',
            marker=dict(color='#cccccc', size=9),
            textfont=dict(color='#aaaaaa', size=10),
            showlegend=False,
        ))
    m = metrics[highlight]
    fig.add_trace(go.Scatter(
        x=[m[x_key]], y=[m[y_key]], mode='markers+text', name=highlight,
        text=[highlight], textposition='top center',
        marker=dict(color=bot_colour[highlight], size=18, line=dict(width=2, color='white')),
        textfont=dict(size=13, color=bot_colour[highlight]),
        showlegend=False,
    ))
    fig.update_layout(
        title=title, xaxis_title=x_label, yaxis_title=y_label,
        **LAYOUT_BASE, margin=dict(t=60, b=60), height=380,
    )
    return fig


def bluff_risk_bubble(players, metrics, bot_colour) -> go.Figure:
    fig = go.Figure()
    for b in players:
        m = metrics[b]
        fig.add_trace(go.Scatter(
            x=[m['bluff_rate']], y=[m['bluff_stealth']],
            mode='markers+text', name=b,
            text=[b], textposition='top center',
            marker=dict(
                color=bot_colour[b], size=14 + m['win_rate'] * 36,
                opacity=0.85, line=dict(width=1.5, color='white'),
            ),
            hovertemplate=(
                f'<b>{b}</b><br>Bluff Rate: %{{x:.1%}}<br>'
                f'Bluff Stealth: %{{y:.1%}}<br>Win Rate: {m["win_rate"]:.1%}<extra></extra>'
            ),
            showlegend=False,
        ))
    fig.update_layout(
        title='Bluffing Risk vs Skill — bubble size = win rate',
        xaxis_title='Bluff Rate (how often they bluff)',
        yaxis_title='Bluff Stealth (fraction that go uncaught)',
        xaxis_tickformat='.0%', yaxis_tickformat='.0%',
        **LAYOUT_BASE, margin=dict(t=60, b=60), height=460,
    )
    return fig


# ── Strategy Analysis ─────────────────────────────────────────────────────────

def by_outcome(metric_fn, title, y_label, y_fmt, players, final_infos) -> go.Figure:
    outcomes = [('hard_wins', 'Hard Win', '#198754'),
                ('soft_wins', 'Soft Win', '#0d6efd'),
                ('losses',    'Loss',     '#dc3545')]
    fig = go.Figure()
    for outcome, label, color in outcomes:
        vals = [metric_fn(getattr(final_infos[b], outcome)) for b in players]
        fig.add_trace(go.Bar(
            name=label, x=players, y=vals, marker_color=color,
            text=[f'{v:{y_fmt}}' for v in vals], textposition='outside',
            hovertemplate=f'<b>%{{x}}</b><br>{label}: %{{y:{y_fmt}}}<extra></extra>',
        ))
    fig.update_layout(
        barmode='group', title=title, yaxis_title=y_label,
        **LAYOUT_BASE, margin=dict(t=60, b=80),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    fig.update_xaxes(tickangle=-35)
    return fig


# ── Head-to-Head ──────────────────────────────────────────────────────────────

def heatmap(position, players, final_infos) -> go.Figure:
    n = len(players)
    matrix = [[None] * n for _ in range(n)]
    text   = [['']   * n for _ in range(n)]
    for i, cur in enumerate(players):
        for j, nbr in enumerate(players):
            wins  = (getattr(final_infos[cur].hard_wins, position).get(nbr, 0)
                     + getattr(final_infos[cur].soft_wins, position).get(nbr, 0))
            total = getattr(final_infos[cur].total, position).get(nbr, 0)
            if total > 0:
                v = wins / total
                matrix[i][j] = round(v, 3)
                text[i][j]   = f'{v:.2f}'
    fig = go.Figure(go.Heatmap(
        z=matrix, x=players, y=players, text=text, texttemplate='%{text}',
        colorscale='RdYlGn', zmin=0, zmax=1, colorbar=dict(title='Win rate'),
        hovertemplate=(
            f'<b>%{{y}}</b> vs <b>%{{x}}</b> ({position} neighbor)<br>'
            f'Win rate: %{{z:.2f}}<extra></extra>'
        ),
    ))
    fig.update_layout(
        title=f'Win Rate vs {position.capitalize()} Neighbor',
        xaxis_title=f'{position.capitalize()} player', yaxis_title='Current player',
        **LAYOUT_BASE, margin=dict(t=60, b=100, l=100),
    )
    fig.update_xaxes(tickangle=-45)
    return fig


# ── Per-Bot ───────────────────────────────────────────────────────────────────

def neighbor_bar(bot, position, players, final_infos, bot_colour) -> go.Figure:
    rates = {}
    for nbr in getattr(final_infos[bot].total, position):
        if nbr == bot:
            continue
        wins  = (getattr(final_infos[bot].hard_wins, position).get(nbr, 0)
                 + getattr(final_infos[bot].soft_wins, position).get(nbr, 0))
        total = getattr(final_infos[bot].total, position).get(nbr, 0)
        if total > 0:
            rates[nbr] = wins / total
    nbrs = sorted(rates, key=lambda x: rates[x], reverse=True)
    vals = [rates[n] for n in nbrs]
    fig = go.Figure(go.Bar(
        x=nbrs, y=vals, marker_color=[bot_colour.get(n, '#888') for n in nbrs],
        text=[f'{v:.1%}' for v in vals], textposition='outside',
        hovertemplate=f'<b>%{{x}}</b> as {position} neighbor<br>Win rate: %{{y:.2%}}<extra></extra>',
    ))
    fig.add_hline(y=0.5, line_dash='dot', line_color='grey')
    fig.update_layout(
        title=f'Win rate when {position} neighbor is…',
        yaxis_title='Win rate', yaxis_tickformat='.0%',
        yaxis_range=[0, max(vals, default=0.5) * 1.2 + 0.05],
        **LAYOUT_BASE, margin=dict(t=50, b=70), height=310,
    )
    fig.update_xaxes(tickangle=-35)
    return fig
