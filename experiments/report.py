import datetime

from .stats import BotStats, safe_div, win_rate, hard_win_rate, soft_win_rate


def _compute_bot_metrics(bot: str, final_infos: dict) -> dict:
    info = final_infos[bot]
    t = info.total
    return {
        'win_rate':       win_rate(info),
        'hard_win_rate':  hard_win_rate(info),
        'soft_win_rate':  soft_win_rate(info),
        'loss_rate':      info.losses.games / t.games if t.games > 0 else 1.0,
        'avg_position':   t.total_position,
        'bluff_rate':     safe_div(t.bluffs, t.play_turns),
        'bluff_stealth':  safe_div(t.bluffs - t.bluff_caught, t.bluffs),
        'doubt_rate':     safe_div(t.doubts, t.not_first_turns),
        'doubt_accuracy': safe_div(t.successful_doubts, t.doubts),
        'cards_per_turn': safe_div(t.cards_played, t.play_turns),
    }


def _neighbor_win_rates(bot: str, data: dict, position: str) -> dict:
    rates = {}
    for neighbor in getattr(data[bot].total, position):
        if neighbor == bot:
            continue
        wins = (getattr(data[bot].hard_wins, position).get(neighbor, 0)
                + getattr(data[bot].soft_wins, position).get(neighbor, 0))
        total = getattr(data[bot].total, position).get(neighbor, 0)
        if total > 0:
            rates[neighbor] = wins / total
    return rates


def _build_heatmap_matrix(data: dict, players: list, position: str):
    n = len(players)
    matrix = [[None] * n for _ in range(n)]
    text   = [[''] * n for _ in range(n)]
    for i, current in enumerate(players):
        for j, neighbour in enumerate(players):
            wins = (getattr(data[current].hard_wins, position).get(neighbour, 0)
                    + getattr(data[current].soft_wins, position).get(neighbour, 0))
            total = getattr(data[current].total, position).get(neighbour, 0)
            if total > 0:
                v = wins / total
                matrix[i][j] = round(v, 3)
                text[i][j]   = f'{v:.2f}'
    return matrix, text


def generate_html_report(final_infos: dict, config: dict, output_path: str = 'report.html') -> None:
    import plotly.graph_objects as go

    players = sorted(final_infos.keys(), key=lambda b: win_rate(final_infos[b]), reverse=True)
    n_bots  = len(players)

    palette = [
        '#4C78A8', '#F58518', '#E45756', '#72B7B2', '#54A24B',
        '#EECA3B', '#B279A2', '#FF9DA7', '#9D755D', '#BAB0AC',
        '#FF7F0E', '#2CA02C', '#D62728', '#9467BD',
    ]
    bot_colour = {b: palette[i % len(palette)] for i, b in enumerate(players)}

    # ── baselines ─────────────────────────────────────────────────────────────
    ap        = config.get('available_players', [5])
    avg_n     = sum(ap) / len(ap)
    hard_base = 1.0 / avg_n
    soft_base = max(0.0, (avg_n - 3) / avg_n)
    win_base  = hard_base + soft_base

    metrics = {b: _compute_bot_metrics(b, final_infos) for b in players}

    # ── auto-generated insights ────────────────────────────────────────────────
    top_bot           = players[0]
    bottom_bot        = players[-1]
    best_bluff_stealth = max(players, key=lambda b: metrics[b]['bluff_stealth'])
    best_doubt_acc    = max(players, key=lambda b: metrics[b]['doubt_accuracy'])
    most_aggressive   = max(players, key=lambda b: metrics[b]['bluff_rate'])
    most_cautious     = min(players, key=lambda b: metrics[b]['bluff_rate'])

    insights = [
        (
            f"<strong>{top_bot}</strong> leads with {metrics[top_bot]['win_rate']:.1%} overall win rate "
            f"({metrics[top_bot]['hard_win_rate']:.1%} hard, {metrics[top_bot]['soft_win_rate']:.1%} soft) — "
            f"{(metrics[top_bot]['win_rate'] - win_base):+.1%} vs baseline."
        ),
        (
            f"<strong>{bottom_bot}</strong> is the weakest performer at {metrics[bottom_bot]['win_rate']:.1%} win rate "
            f"({(metrics[bottom_bot]['win_rate'] - win_base):+.1%} vs baseline)."
        ),
        (
            f"<strong>{best_bluff_stealth}</strong> is the sneakiest bluffer: "
            f"{metrics[best_bluff_stealth]['bluff_stealth']:.1%} of bluffs go uncaught. "
            f"<strong>{best_doubt_acc}</strong> has the sharpest doubt instinct at "
            f"{metrics[best_doubt_acc]['doubt_accuracy']:.1%} accuracy."
        ),
        (
            f"<strong>{most_aggressive}</strong> bluffs most aggressively ({metrics[most_aggressive]['bluff_rate']:.1%} of turns); "
            f"<strong>{most_cautious}</strong> plays it straight ({metrics[most_cautious]['bluff_rate']:.1%})."
        ),
    ]

    # ── layout helper ─────────────────────────────────────────────────────────
    LAYOUT_BASE = dict(
        plot_bgcolor='white', paper_bgcolor='white',
        font_family='Inter, sans-serif',
    )

    def _div(fig, div_id: str = '', height: str = '420px') -> str:
        kwargs = dict(full_html=False, include_plotlyjs=False, config={'responsive': True})
        if div_id:
            kwargs['div_id'] = div_id
        return f'<div style="width:100%;height:{height};">{fig.to_html(**kwargs)}</div>'

    # ── Section 1 chart: win-type scatter ─────────────────────────────────────
    fig_win_space = go.Figure()
    for b in players:
        m = metrics[b]
        fig_win_space.add_trace(go.Scatter(
            x=[m['hard_win_rate']], y=[m['soft_win_rate']],
            mode='markers+text', name=b, text=[b], textposition='top center',
            marker=dict(color=bot_colour[b], size=14),
            hovertemplate=(
                f'<b>{b}</b><br>'
                f'Hard Win %: %{{x:.1%}}<br>'
                f'Soft Win %: %{{y:.1%}}<extra></extra>'
            ),
            showlegend=False,
        ))
    fig_win_space.add_vline(x=hard_base, line_dash='dot', line_color='crimson',
                            annotation_text=f'Hard baseline ({hard_base:.1%})',
                            annotation_position='top right')
    fig_win_space.add_hline(y=soft_base, line_dash='dot', line_color='steelblue',
                            annotation_text=f'Soft baseline ({soft_base:.1%})',
                            annotation_position='top left')
    fig_win_space.update_layout(
        title='Win-Type Space: Hard Win % vs Soft Win %',
        xaxis_title='Hard Win % (1st place)', yaxis_title='Soft Win % (2nd–n−2)',
        xaxis_tickformat='.0%', yaxis_tickformat='.0%',
        **LAYOUT_BASE, margin=dict(t=60, b=60), height=480,
    )

    # ── Section 2 chart: overall win rate bar ────────────────────────────────
    win_rates = [metrics[b]['win_rate'] for b in players]
    fig_wr = go.Figure()
    fig_wr.add_trace(go.Bar(
        x=players, y=win_rates,
        marker_color=[bot_colour[b] for b in players],
        text=[f'{v:.1%}' for v in win_rates],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Win rate: %{y:.2%}<extra></extra>',
    ))
    fig_wr.add_hline(y=win_base, line_dash='dot', line_color='crimson',
                     annotation_text=f'Baseline ({win_base:.1%})',
                     annotation_position='top right')
    fig_wr.update_layout(
        title='Overall Win Rate by Bot (Hard + Soft Wins)',
        yaxis_title='Win Rate', yaxis_tickformat='.0%',
        yaxis_range=[0, max(win_rates) * 1.15],
        **LAYOUT_BASE, margin=dict(t=60, b=80),
    )
    fig_wr.update_xaxes(tickangle=-35)

    # ── Section 2 chart: outcome composition stacked bar ─────────────────────
    hard_pcts = [metrics[b]['hard_win_rate'] for b in players]
    soft_pcts = [metrics[b]['soft_win_rate'] for b in players]
    loss_pcts = [metrics[b]['loss_rate'] for b in players]

    fig_outcome = go.Figure()
    fig_outcome.add_trace(go.Bar(
        name='Hard Win (1st)', x=players, y=hard_pcts,
        marker_color='#198754',
        text=[f'{v:.1%}' for v in hard_pcts], textposition='inside',
        insidetextanchor='middle',
        hovertemplate='<b>%{x}</b><br>Hard Win: %{y:.2%}<extra></extra>',
    ))
    fig_outcome.add_trace(go.Bar(
        name='Soft Win (2nd+)', x=players, y=soft_pcts,
        marker_color='#0d6efd',
        text=[f'{v:.1%}' for v in soft_pcts], textposition='inside',
        insidetextanchor='middle',
        hovertemplate='<b>%{x}</b><br>Soft Win: %{y:.2%}<extra></extra>',
    ))
    fig_outcome.add_trace(go.Bar(
        name='Loss (last)', x=players, y=loss_pcts,
        marker_color='#dc3545',
        text=[f'{v:.1%}' for v in loss_pcts], textposition='inside',
        insidetextanchor='middle',
        hovertemplate='<b>%{x}</b><br>Loss: %{y:.2%}<extra></extra>',
    ))
    fig_outcome.update_layout(
        barmode='stack', title='Outcome Composition per Bot',
        yaxis_title='Fraction of games', yaxis_tickformat='.0%',
        **LAYOUT_BASE, margin=dict(t=60, b=80),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    fig_outcome.update_xaxes(tickangle=-35)

    # ── Section 2 chart: avg relative position ───────────────────────────────
    pos_bots = sorted(players, key=lambda b: metrics[b]['avg_position'], reverse=True)
    pos_vals = [metrics[b]['avg_position'] for b in pos_bots]
    fig_pos = go.Figure()
    fig_pos.add_trace(go.Bar(
        x=pos_bots, y=pos_vals,
        marker_color=[bot_colour[b] for b in pos_bots],
        text=[f'{v:.2f}' for v in pos_vals], textposition='outside',
        hovertemplate='<b>%{x}</b><br>Avg relative position: %{y:.3f}<extra></extra>',
    ))
    fig_pos.add_hline(y=0.5, line_dash='dot', line_color='crimson',
                      annotation_text='Random baseline (0.5)', annotation_position='top right')
    fig_pos.update_layout(
        title='Avg Relative Finish Position (1.0 = always 1st, 0.0 = always last)',
        yaxis_title='Relative position', yaxis_range=[0, 1.15],
        **LAYOUT_BASE, margin=dict(t=60, b=80),
    )
    fig_pos.update_xaxes(tickangle=-35)

    # ── Section 2 chart: avg cards grouped bar ───────────────────────────────
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
    fig_cards = go.Figure()
    for label, vals, opacity in [('Total', avg_total, 1.0), ('On wins', avg_wins, 0.75), ('On losses', avg_losses, 0.5)]:
        fig_cards.add_trace(go.Bar(
            name=label, x=players, y=vals,
            marker_color=[bot_colour[b] for b in players],
            marker_opacity=opacity,
            text=[f'{v:.2f}' for v in vals], textposition='outside',
            hovertemplate=f'<b>%{{x}}</b><br>{label}: %{{y:.2f}} cards<extra></extra>',
        ))
    fig_cards.update_layout(
        barmode='group', title='Average Cards in Hand at Game End',
        yaxis_title='Avg cards',
        **LAYOUT_BASE, margin=dict(t=60, b=80),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    fig_cards.update_xaxes(tickangle=-35)

    # ── Section 3 chart: behavioral radar ────────────────────────────────────
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
    max_cpt = max((axes_raw[b]['Cards per Turn'] for b in players), default=1) or 1
    for b in players:
        axes_raw[b]['Cards per Turn'] /= max_cpt

    axis_labels = ['Win Rate', 'Bluff Rate', 'Bluff Stealth', 'Doubt Rate', 'Doubt Accuracy', 'Cards per Turn']
    axis_labels_closed = axis_labels + [axis_labels[0]]

    fig_radar = go.Figure()
    for bot in players:
        vals = [axes_raw[bot][a] for a in axis_labels]
        vals_closed = vals + [vals[0]]
        fig_radar.add_trace(go.Scatterpolar(
            r=vals_closed, theta=axis_labels_closed, name=bot,
            line_color=bot_colour[bot], fill='toself',
            fillcolor=bot_colour[bot], opacity=0.15,
            hovertemplate=(
                f'<b>{bot}</b><br>'
                + '<br>'.join(f'{a}: %{{r[{i}]:.2f}}' for i, a in enumerate(axis_labels))
                + '<extra></extra>'
            ),
        ))
    fig_radar.update_layout(
        title='Behavioral Fingerprint (click legend to toggle)',
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], tickformat='.0%'),
            angularaxis=dict(tickfont=dict(size=12)),
        ),
        showlegend=True,
        legend=dict(orientation='v', x=1.05, y=0.5),
        **LAYOUT_BASE,
        margin=dict(t=60, b=40, l=60, r=180), height=560,
    )

    # ── Section 3 scatter helper ──────────────────────────────────────────────
    def _scatter(x_key, y_key, x_label, y_label, title, x_fmt='.2f', y_fmt='.2f') -> go.Figure:
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

    fig_sc_style   = _scatter('bluff_rate',    'doubt_rate',     'Bluff Rate',            'Doubt Rate',    'Style Space: Bluff Rate vs Doubt Rate',           '.1%', '.1%')
    fig_sc_quality = _scatter('bluff_stealth', 'doubt_accuracy', 'Bluff Stealth',         'Doubt Accuracy', 'Deception Quality: Bluff Stealth vs Doubt Accuracy', '.1%', '.1%')
    fig_sc_agg_wr  = _scatter('bluff_rate',    'win_rate',       'Bluff Rate',            'Win Rate',       'Does Aggression Pay Off? Bluff Rate vs Win Rate',    '.1%', '.1%')
    fig_sc_pos_wr  = _scatter('avg_position',  'win_rate',       'Avg Relative Position', 'Win Rate',       'Position vs Win Rate',                              '.3f', '.1%')

    # ── Section 4 chart: bluff rate by outcome ───────────────────────────────
    outcomes       = ['hard_wins', 'soft_wins', 'losses']
    outcome_labels = ['Hard Win', 'Soft Win', 'Loss']
    outcome_colors = ['#198754', '#0d6efd', '#dc3545']

    fig_bluff_outcome = go.Figure()
    for outcome, label, color in zip(outcomes, outcome_labels, outcome_colors):
        vals = [
            safe_div(getattr(final_infos[b], outcome).bluffs,
                     getattr(final_infos[b], outcome).play_turns)
            for b in players
        ]
        fig_bluff_outcome.add_trace(go.Bar(
            name=label, x=players, y=vals, marker_color=color,
            text=[f'{v:.1%}' for v in vals], textposition='outside',
            hovertemplate=f'<b>%{{x}}</b><br>Bluff rate ({label}): %{{y:.2%}}<extra></extra>',
        ))
    fig_bluff_outcome.update_layout(
        barmode='group',
        title='Bluff Rate by Outcome — do winners bluff more or less?',
        yaxis_title='Bluff Rate', yaxis_tickformat='.0%',
        **LAYOUT_BASE, margin=dict(t=60, b=80),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    fig_bluff_outcome.update_xaxes(tickangle=-35)

    # ── Section 4 chart: doubt accuracy by outcome ───────────────────────────
    fig_doubt_outcome = go.Figure()
    for outcome, label, color in zip(outcomes, outcome_labels, outcome_colors):
        vals = [
            safe_div(getattr(final_infos[b], outcome).successful_doubts,
                     getattr(final_infos[b], outcome).doubts)
            for b in players
        ]
        fig_doubt_outcome.add_trace(go.Bar(
            name=label, x=players, y=vals, marker_color=color,
            text=[f'{v:.1%}' for v in vals], textposition='outside',
            hovertemplate=f'<b>%{{x}}</b><br>Doubt accuracy ({label}): %{{y:.2%}}<extra></extra>',
        ))
    fig_doubt_outcome.update_layout(
        barmode='group',
        title='Doubt Accuracy by Outcome — are winners better at calling bluffs?',
        yaxis_title='Doubt Accuracy', yaxis_tickformat='.0%',
        **LAYOUT_BASE, margin=dict(t=60, b=80),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    fig_doubt_outcome.update_xaxes(tickangle=-35)

    # ── Section 5 chart: heatmaps ─────────────────────────────────────────────
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
            **LAYOUT_BASE, margin=dict(t=60, b=100, l=100),
        )
        fig.update_xaxes(tickangle=-45)
        return fig

    fig_hm_prev = _heatmap_fig('prev', 'Win Rate vs Prev Neighbor')
    fig_hm_next = _heatmap_fig('next', 'Win Rate vs Next Neighbor')

    # ── per-bot neighbor charts ───────────────────────────────────────────────
    def _neighbor_fig(bot: str, position: str) -> go.Figure:
        rates   = _neighbor_win_rates(bot, final_infos, position)
        nbrs    = sorted(rates, key=lambda x: rates[x], reverse=True)
        vals    = [rates[n] for n in nbrs]
        colours = [bot_colour.get(n, '#888') for n in nbrs]
        fig = go.Figure(go.Bar(
            x=nbrs, y=vals, marker_color=colours,
            text=[f'{v:.1%}' for v in vals], textposition='outside',
            hovertemplate=f'<b>%{{x}}</b> as {position} neighbor<br>Win rate: %{{y:.2%}}<extra></extra>',
        ))
        fig.add_hline(y=0.5, line_dash='dot', line_color='grey')
        fig.update_layout(
            title=f'{position.capitalize()} neighbor win rate',
            yaxis_title='Win rate', yaxis_tickformat='.0%',
            yaxis_range=[0, max(vals, default=0.5) * 1.2 + 0.05],
            **LAYOUT_BASE, margin=dict(t=50, b=70), height=300,
        )
        fig.update_xaxes(tickangle=-35)
        return fig

    # ── leaderboard table rows ────────────────────────────────────────────────
    def _table_rows(sorted_bots: list, rate_fn, base: float, bucket: str) -> str:
        rows = ''
        for rank, bot in enumerate(sorted_bots, 1):
            info   = final_infos[bot]
            rate   = rate_fn(info)
            colour = bot_colour[bot]
            badge  = f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{colour};margin-right:6px;"></span>'
            delta  = rate - base
            rows += f'''
        <tr>
          <td class="text-center text-muted">{rank}</td>
          <td><a href="#{bot}" class="text-decoration-none fw-semibold">{badge}{bot}</a></td>
          <td class="text-end">{info.total.games:,}</td>
          <td class="text-end">{getattr(info, bucket).games:,}</td>
          <td class="text-end fw-bold" style="color:{colour}">{rate:.1%}</td>
          <td class="text-end">{getattr(info, bucket).avg_cards:.2f}</td>
          <td class="text-end" style="color:{'#198754' if delta >= 0 else '#dc3545'};">{delta:+.1%}</td>
          <td class="text-end text-danger">{info.losses.avg_cards:.2f}</td>
        </tr>'''
        return rows

    hard_rows = _table_rows(
        sorted(players, key=lambda b: hard_win_rate(final_infos[b]), reverse=True),
        hard_win_rate, hard_base, 'hard_wins',
    )
    soft_rows = _table_rows(
        sorted(players, key=lambda b: soft_win_rate(final_infos[b]), reverse=True),
        soft_win_rate, soft_base, 'soft_wins',
    )

    # ── per-bot section HTML ──────────────────────────────────────────────────
    bot_sections = ''
    for bot in players:
        info    = final_infos[bot]
        hwr     = hard_win_rate(info)
        swr     = soft_win_rate(info)
        colour  = bot_colour[bot]
        rank    = players.index(bot) + 1
        m       = metrics[bot]
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
        <p class="text-muted small mb-3">Performance &amp; outcome distribution</p>
        <div class="row g-2 mb-3">
          <div class="col-6 col-md-2">
            <div class="stat-card"><div class="stat-value">{info.total.games:,}</div><div class="stat-label">Total games</div></div>
          </div>
          <div class="col-6 col-md-2">
            <div class="stat-card">
              <div class="stat-value" style="color:{colour};">{hwr:.1%}</div>
              <div class="stat-label">Hard Win %</div>
              <div class="progress mt-1" style="height:4px;"><div class="progress-bar" style="width:{int(hwr*100)}%;background:{colour};"></div></div>
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
              <div class="stat-value text-primary">{swr:.1%}</div>
              <div class="stat-label">Soft Win %</div>
              <div class="progress mt-1" style="height:4px;"><div class="progress-bar bg-primary" style="width:{int(swr*100)}%;"></div></div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="stat-card">
              <div class="stat-value" style="color:{'#198754' if swr >= soft_base else '#dc3545'};">{(swr - soft_base):+.1%}</div>
              <div class="stat-label">vs Soft Baseline</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="stat-card"><div class="stat-value text-danger">{info.losses.avg_cards:.2f}</div><div class="stat-label">Avg cards on loss</div></div>
          </div>
        </div>
        <p class="text-muted small mb-3">Behavioral profile</p>
        <div class="row g-2 mb-3">
          <div class="col-6 col-md-3">
            <div class="stat-card"><div class="stat-value">{m['bluff_rate']:.1%}</div><div class="stat-label">Bluff Rate</div></div>
          </div>
          <div class="col-6 col-md-3">
            <div class="stat-card"><div class="stat-value">{m['bluff_stealth']:.1%}</div><div class="stat-label">Bluff Stealth</div></div>
          </div>
          <div class="col-6 col-md-3">
            <div class="stat-card"><div class="stat-value">{m['doubt_rate']:.1%}</div><div class="stat-label">Doubt Rate</div></div>
          </div>
          <div class="col-6 col-md-3">
            <div class="stat-card"><div class="stat-value">{m['doubt_accuracy']:.1%}</div><div class="stat-label">Doubt Accuracy</div></div>
          </div>
        </div>
        <p class="text-muted small mb-3">Win rate when adjacent to each neighbor</p>
        <div class="row g-3">
          <div class="col-md-6">{prev_div}</div>
          <div class="col-md-6">{next_div}</div>
        </div>
      </div>
    </div>'''

    # ── assemble full HTML ────────────────────────────────────────────────────
    n_exp     = config.get('n_experiments', '?')
    ap_str    = f'{ap[0]}–{ap[-1]}' if ap else '?'
    generated = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

    insights_html = ''.join(f'<li>{i}</li>' for i in insights)

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
    .navbar-brand {{ font-weight:700; letter-spacing:.5px; }}
    .nav-link {{ color: rgba(255,255,255,.65) !important; font-size:.85rem; padding:.25rem .5rem !important; }}
    .nav-link:hover {{ color:#fff !important; }}
    section {{ scroll-margin-top:70px; }}
    .stat-card {{ background:#fff; border:1px solid #e9ecef; border-radius:8px; padding:12px 16px; text-align:center; height:100%; }}
    .stat-value {{ font-size:1.4rem; font-weight:700; }}
    .stat-label {{ font-size:.75rem; color:#6c757d; text-transform:uppercase; letter-spacing:.5px; }}
    .chart-card {{ background:#fff; border:1px solid #e9ecef; border-radius:10px; padding:16px; }}
    table thead th {{ background:#343a40; color:#fff; white-space:nowrap; }}
    .section-title {{ font-size:1.4rem; font-weight:700; border-left:4px solid #4C78A8; padding-left:12px; margin-bottom:.5rem; }}
    .config-badge {{ display:inline-block; background:#e9ecef; border-radius:20px; padding:4px 14px; font-size:.85rem; font-weight:600; margin:2px; }}
    a[href^="#"] {{ color:inherit; }}
    .insight-list {{ list-style:none; padding:0; margin:0; }}
    .insight-list li {{ padding:5px 0 5px 1.5rem; border-bottom:1px solid rgba(255,255,255,.15); position:relative; }}
    .insight-list li:last-child {{ border-bottom:none; }}
    .insight-list li::before {{ content:"›"; position:absolute; left:0; font-weight:700; color:#EECA3B; }}
  </style>
</head>
<body>

<nav class="navbar navbar-dark bg-dark sticky-top px-4">
  <span class="navbar-brand">🎴 Dubito Experiment Report</span>
  <ul class="navbar-nav flex-row gap-1 d-none d-xl-flex">
    <li class="nav-item"><a class="nav-link" href="#leaderboard">Leaderboard</a></li>
    <li class="nav-item"><a class="nav-link" href="#rankings">Rankings</a></li>
    <li class="nav-item"><a class="nav-link" href="#behavior">Behavior</a></li>
    <li class="nav-item"><a class="nav-link" href="#strategy">Strategy</a></li>
    <li class="nav-item"><a class="nav-link" href="#h2h">Head-to-Head</a></li>
    <li class="nav-item"><a class="nav-link" href="#bots">Per-Bot</a></li>
  </ul>
  <span class="text-white-50 small">Generated {generated}</span>
</nav>

<div class="container-lg py-4">

  <!-- Config + Insights banner -->
  <div class="alert alert-dark mb-4">
    <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
      <strong>Experiment config:</strong>
      <span class="config-badge">🎲 {n_exp:,} games</span>
      <span class="config-badge">👥 {ap_str} players/game</span>
      <span class="config-badge">🤖 {n_bots} bots</span>
    </div>
    <ul class="insight-list">
      {insights_html}
    </ul>
  </div>

  <!-- ── Section 1: Leaderboard ────────────────────────────────────────────── -->
  <section id="leaderboard" class="mb-5">
    <div class="section-title">Leaderboard</div>

    <p class="text-muted small mb-2">
      A <strong>hard win</strong> means finishing 1st (first to empty their hand).
      Baseline ≈ {hard_base:.1%} (1 / avg players).
    </p>
    <div class="table-responsive mb-4">
      <table class="table table-hover table-bordered align-middle mb-0 bg-white shadow-sm">
        <thead><tr>
          <th class="text-center">#</th><th>Bot</th>
          <th class="text-end">Total games</th><th class="text-end">Hard Wins</th>
          <th class="text-end">Hard Win %</th><th class="text-end">Avg cards (win)</th>
          <th class="text-end">vs Baseline</th><th class="text-end">Avg cards (loss)</th>
        </tr></thead>
        <tbody>{hard_rows}</tbody>
      </table>
    </div>

    <p class="text-muted small mb-2">
      A <strong>soft win</strong> means emptying hand while ≥3 players remain active (2nd to n−2 place).
      Baseline ≈ {soft_base:.1%} ((avg players − 3) / avg players).
    </p>
    <div class="table-responsive mb-4">
      <table class="table table-hover table-bordered align-middle mb-0 bg-white shadow-sm">
        <thead><tr>
          <th class="text-center">#</th><th>Bot</th>
          <th class="text-end">Total games</th><th class="text-end">Soft Wins</th>
          <th class="text-end">Soft Win %</th><th class="text-end">Avg cards (win)</th>
          <th class="text-end">vs Baseline</th><th class="text-end">Avg cards (loss)</th>
        </tr></thead>
        <tbody>{soft_rows}</tbody>
      </table>
    </div>

    <div class="chart-card">
      {_div(fig_win_space, height='500px')}
      <p class="text-muted small mt-2 mb-0 text-center">
        Top-right = strong at both win types.
        Right of the red line = above hard-win baseline.
        Above the blue line = above soft-win baseline.
      </p>
    </div>
  </section>

  <!-- ── Section 2: Rankings ───────────────────────────────────────────────── -->
  <section id="rankings" class="mb-5">
    <div class="section-title">Rankings</div>
    <div class="row g-4">
      <div class="col-12">
        <div class="chart-card">{_div(fig_wr, height='440px')}</div>
      </div>
      <div class="col-12">
        <div class="chart-card">
          {_div(fig_outcome, height='460px')}
          <p class="text-muted small mt-2 mb-0 text-center">
            Each bar sums to 100%. Hard Win = 1st place, Soft Win = 2nd–n−2, Loss = last.
          </p>
        </div>
      </div>
      <div class="col-12">
        <div class="chart-card">{_div(fig_pos, height='440px')}</div>
      </div>
      <div class="col-12">
        <div class="chart-card">{_div(fig_cards, height='440px')}</div>
      </div>
    </div>
  </section>

  <!-- ── Section 3: Behavioral Profiles ───────────────────────────────────── -->
  <section id="behavior" class="mb-5">
    <div class="section-title">Behavioral Profiles</div>
    <div class="row g-4">
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
      <div class="col-12 col-xl-6">
        <div class="chart-card">
          {_div(fig_sc_style, height='440px')}
          <p class="text-muted small mt-1 mb-0 text-center">
            Bots in the top-right corner are high-bluff, high-doubt — the most active players.
          </p>
        </div>
      </div>
      <div class="col-12 col-xl-6">
        <div class="chart-card">
          {_div(fig_sc_quality, height='440px')}
          <p class="text-muted small mt-1 mb-0 text-center">
            Top-right = good at both hiding bluffs and catching others'.
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- ── Section 4: Strategy Analysis ─────────────────────────────────────── -->
  <section id="strategy" class="mb-5">
    <div class="section-title">Strategy Analysis</div>
    <div class="row g-4">
      <div class="col-12 col-xl-6">
        <div class="chart-card">
          {_div(fig_sc_agg_wr, height='440px')}
          <p class="text-muted small mt-1 mb-0 text-center">
            Does bluffing more often lead to winning? Look for a trend (or lack of one).
          </p>
        </div>
      </div>
      <div class="col-12 col-xl-6">
        <div class="chart-card">
          {_div(fig_sc_pos_wr, height='440px')}
          <p class="text-muted small mt-1 mb-0 text-center">
            Win rate should correlate strongly with avg relative position (sanity check).
          </p>
        </div>
      </div>
      <div class="col-12">
        <div class="chart-card">
          {_div(fig_bluff_outcome, height='460px')}
          <p class="text-muted small mt-1 mb-0 text-center">
            Compare bluff rates across outcomes. If Hard Win bars are higher, bluffing tends to win; if Loss bars dominate, it backfires.
          </p>
        </div>
      </div>
      <div class="col-12">
        <div class="chart-card">
          {_div(fig_doubt_outcome, height='460px')}
          <p class="text-muted small mt-1 mb-0 text-center">
            Do bots doubt more accurately when they win? A gap between Hard Win and Loss bars reveals whether doubt quality influences outcomes.
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- ── Section 5: Head-to-Head ───────────────────────────────────────────── -->
  <section id="h2h" class="mb-5">
    <div class="section-title">Head-to-Head</div>
    <p class="text-muted small mb-3">
      Win rate of the <strong>row bot</strong> when the <strong>column bot</strong> is the adjacent (prev/next) neighbor.
      Diagonal entries are excluded (a bot is never its own neighbor).
    </p>
    <div class="row g-4">
      <div class="col-12 col-xl-6"><div class="chart-card">{_div(fig_hm_prev, height='520px')}</div></div>
      <div class="col-12 col-xl-6"><div class="chart-card">{_div(fig_hm_next, height='520px')}</div></div>
    </div>
  </section>

  <!-- ── Section 6: Per-Bot Breakdown ──────────────────────────────────────── -->
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
