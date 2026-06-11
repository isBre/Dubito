import datetime
import json
import os

from ..stats import safe_div, win_rate, hard_win_rate, soft_win_rate
from . import _charts as C
from ._common import (
    make_bot_colours, div, head, nav, foot,
    stat_card, chart_card, tip_box,
)


# ── Metrics ───────────────────────────────────────────────────────────────────

def _metrics(bot: str, final_infos: dict) -> dict:
    info = final_infos[bot]
    t    = info.total
    return {
        'win_rate':       win_rate(info),
        'hard_win_rate':  hard_win_rate(info),
        'soft_win_rate':  soft_win_rate(info),
        'loss_rate':      safe_div(info.losses.games, t.games, fallback=1.0),
        'avg_position':   t.total_position,
        'bluff_rate':     safe_div(t.bluffs, t.play_turns),
        'bluff_stealth':  safe_div(t.bluffs - t.bluff_caught, t.bluffs),
        'doubt_rate':     safe_div(t.doubts, t.not_first_turns),
        'doubt_accuracy': safe_div(t.successful_doubts, t.doubts),
        'cards_per_turn': safe_div(t.cards_played, t.play_turns),
        'games':          t.games,
    }


def _all_metrics(players: list, final_infos: dict) -> dict:
    return {b: _metrics(b, final_infos) for b in players}



def _bot_tips(bot, metrics) -> str:
    m = metrics[bot]
    lines = []
    br = m['bluff_rate']
    bs = m['bluff_stealth']
    dr = m['doubt_rate']
    da = m['doubt_accuracy']

    if br > 0.35:
        lines.append(f'<strong>Bluffs very frequently ({br:.0%}).</strong> '
                     'When facing this bot, doubt aggressively — most of its plays are dishonest.')
    elif br < 0.10:
        lines.append(f'<strong>Almost never bluffs ({br:.0%}).</strong> '
                     'Doubting against this bot is risky; trust its plays and save doubts for others.')
    else:
        lines.append(f'<strong>Bluffs moderately ({br:.0%}).</strong> '
                     'Stay alert but don\'t over-commit to doubting — pick your spots.')

    if bs > 0.75:
        lines.append(f'Its bluffs are hard to detect ({bs:.0%} go uncaught). '
                     'If you decide to doubt, rely on context rather than just intuition.')
    elif bs < 0.40:
        lines.append(f'Its bluffs get caught often ({100 - bs * 100:.0f}% caught). '
                     'Doubting pays off more than usual against this bot.')

    if da > 0.70:
        lines.append(f'<strong>Excellent doubt instinct ({da:.0%} accuracy).</strong> '
                     'Be careful bluffing — this bot will call you out.')
    elif da < 0.45:
        lines.append(f'<strong>Poor doubt instinct ({da:.0%} accuracy).</strong> '
                     'Bluffing is comparatively safer; it doubts too often and gets it wrong.')

    if dr > 0.30:
        lines.append(f'Doubts very frequently ({dr:.0%} of eligible turns). '
                     'Avoid large bluffs and keep your dishonest plays small.')

    return '<ul class="mb-0">' + ''.join(f'<li>{l}</li>' for l in lines) + '</ul>'


# ── Shared table helper ────────────────────────────────────────────────────────

def _leaderboard_rows(sorted_bots, rate_fn, base, bucket, final_infos, bot_colour, prefix='') -> str:
    rows = ''
    for rank, bot in enumerate(sorted_bots, 1):
        info   = final_infos[bot]
        rate   = rate_fn(info)
        colour = bot_colour[bot]
        delta  = rate - base
        dot    = (f'<span style="display:inline-block;width:11px;height:11px;'
                  f'border-radius:50%;background:{colour};margin-right:7px;"></span>')
        rows += f'''
      <tr>
        <td class="text-center text-muted">{rank}</td>
        <td><a href="{prefix}bots/{bot}.html" class="text-decoration-none fw-semibold">{dot}{bot}</a></td>
        <td class="text-end">{info.total.games:,}</td>
        <td class="text-end">{getattr(info, bucket).games:,}</td>
        <td class="text-end fw-bold" style="color:{colour}">{rate:.1%}</td>
        <td class="text-end">{getattr(info, bucket).avg_cards:.2f}</td>
        <td class="text-end" style="color:{'#198754' if delta >= 0 else '#dc3545'}">{delta:+.1%}</td>
        <td class="text-end text-danger">{info.losses.avg_cards:.2f}</td>
      </tr>'''
    return rows


# ── Overview table (sorted by overall = hard + soft win rate) ─────────────────

def _overview_rows(players, final_infos, metrics, bot_colour, win_base, prefix='') -> str:
    rows = ''
    for rank, bot in enumerate(
        sorted(players, key=lambda b: metrics[b]['win_rate'], reverse=True), 1
    ):
        info   = final_infos[bot]
        m      = metrics[bot]
        colour = bot_colour[bot]
        delta  = m['win_rate'] - win_base
        dot    = (f'<span style="display:inline-block;width:11px;height:11px;'
                  f'border-radius:50%;background:{colour};margin-right:7px;"></span>')
        rows += f'''
      <tr>
        <td class="text-center text-muted">{rank}</td>
        <td><a href="{prefix}bots/{bot}.html" class="text-decoration-none fw-semibold">{dot}{bot}</a></td>
        <td class="text-end">{info.total.games:,}</td>
        <td class="text-end fw-bold" style="color:{colour}">{m['win_rate']:.1%}</td>
        <td class="text-end" style="color:{'#198754' if delta >= 0 else '#dc3545'}">{delta:+.1%}</td>
        <td class="text-end">{m['hard_win_rate']:.1%}</td>
        <td class="text-end">{m['soft_win_rate']:.1%}</td>
        <td class="text-end text-danger">{info.losses.avg_cards:.2f}</td>
      </tr>'''
    return rows


# ── Pages ─────────────────────────────────────────────────────────────────────

def _page_index(players, final_infos, metrics, bot_colour, baselines,
                config, generated) -> str:
    hard_base, soft_base, win_base = baselines
    n_exp  = config.get('n_experiments', '?')
    ap     = config.get('available_players', [5])
    ap_str = f'{ap[0]}–{ap[-1]}' if ap else '?'
    n_bots = len(players)

    table_rows = _overview_rows(players, final_infos, metrics, bot_colour, win_base)

    win_scatter = div(C.win_type_scatter(players, metrics, bot_colour, hard_base, soft_base), height='460px')

    bot_cards = ''.join(
        f'<div class="col-6 col-md-4 col-lg-3">'
        f'<a href="bots/{b}.html" class="nav-card text-center">'
        f'<div style="width:40px;height:40px;border-radius:50%;background:{bot_colour[b]};'
        f'margin:0 auto 8px;"></div>'
        f'<div class="fw-semibold small">{b}</div>'
        f'<div class="text-muted" style="font-size:.75rem;">'
        f'#{i+1} · {metrics[b]["win_rate"]:.1%}</div>'
        f'</a></div>'
        for i, b in enumerate(players)
    )

    return head('Overview') + nav(players, bot_colour, 'overview') + f'''
<div class="container-lg py-4">

  <!-- Hero -->
  <div class="mb-4">
    <h1 class="fw-bold mb-1">🎴 Dubito Bot Report</h1>
    <p class="text-muted lead mb-0">
      Experiment results: <strong>{n_exp:,} games</strong>,
      <strong>{n_bots} bots</strong>,
      <strong>{ap_str} players per game</strong>.
    </p>
  </div>

  <!-- Navigation cards -->
  <div class="row g-3 mb-5">
    <div class="col-md-4">
      <a href="strategy.html" class="nav-card">
        <div class="fw-bold mb-1">📊 Strategy Guide</div>
        <div class="text-muted small">Cross-bot charts with educational captions. Learn what separates winners from losers.</div>
      </a>
    </div>
    <div class="col-md-4">
      <a href="compare.html" class="nav-card">
        <div class="fw-bold mb-1">⚖️ Compare Bots</div>
        <div class="text-muted small">Pick any set of bots and compare their stats, radar profiles, and outcomes side by side.</div>
      </a>
    </div>
    <div class="col-md-4">
      <a href="bots/{players[0]}.html" class="nav-card">
        <div class="fw-bold mb-1">🤖 Browse Bots</div>
        <div class="text-muted small">Deep-dive pages for every bot — stats, neighbor analysis, and tips on how to play against them.</div>
      </a>
    </div>
  </div>

  <!-- Leaderboard table -->
  <section id="leaderboard" class="mb-5">
    <div class="section-title">Leaderboard</div>
    <p class="text-muted small mb-2">
      Sorted by <strong>Overall Win %</strong> = hard wins + soft wins (i.e. "not finishing last").
      In an <em>n</em>-player game exactly 2 players lose, so the baseline is
      <strong>{win_base:.1%}</strong> ((n−2)/n, avg across game sizes {ap_str}).
      A <strong>hard win</strong> = 1st place; a <strong>soft win</strong> = any middle finish.
      Click any bot name to open its detail page.
    </p>
    <div class="table-responsive mb-4">
      <table class="table table-hover table-bordered align-middle bg-white shadow-sm mb-0">
        <thead><tr>
          <th class="text-center">#</th><th>Bot</th>
          <th class="text-end">Total games</th>
          <th class="text-end">Overall Win %</th>
          <th class="text-end">vs Baseline</th>
          <th class="text-end">Hard Win %</th>
          <th class="text-end">Soft Win %</th>
          <th class="text-end">Avg cards (loss)</th>
        </tr></thead>
        <tbody>{table_rows}</tbody>
      </table>
    </div>
  </section>

  <!-- Win-type scatter -->
  <section id="overview-chart" class="mb-5">
    <div class="section-title">Win-Type Overview</div>
    {chart_card(win_scatter,
      'Top-right = strong at both win types. '
      'Right of the red line = above hard-win baseline. '
      'Above the blue line = above soft-win baseline.')}
  </section>

  <!-- All bots grid -->
  <section id="all-bots" class="mb-5">
    <div class="section-title">All Bots</div>
    <div class="row g-2">{bot_cards}</div>
  </section>

</div>
''' + foot(generated)


def _page_strategy(players, final_infos, metrics, bot_colour, baselines,
                   config, generated) -> str:
    hard_base, soft_base, win_base = baselines

    def _d(fig, h='440px'): return div(fig, h)

    wr_chart     = _d(C.win_rate_bar(players, metrics, bot_colour, win_base))
    outcome_chart= _d(C.outcome_composition(players, metrics), '460px')
    pos_chart    = _d(C.avg_position(players, metrics, bot_colour))
    cards_chart  = _d(C.avg_cards(players, final_infos, bot_colour))
    radar_chart  = _d(C.radar(players, metrics, bot_colour), '560px')
    style_chart  = _d(C.scatter('bluff_rate', 'doubt_rate', 'Bluff Rate', 'Doubt Rate',
                                'Style Space: Bluff Rate vs Doubt Rate', players, metrics, bot_colour))
    qual_chart   = _d(C.scatter('bluff_stealth', 'doubt_accuracy', 'Bluff Stealth', 'Doubt Accuracy',
                                'Deception Quality: Bluff Stealth vs Doubt Accuracy', players, metrics, bot_colour))
    bubble_chart = _d(C.bluff_risk_bubble(players, metrics, bot_colour), '460px')
    parco_chart  = _d(C.parcoords(players, metrics, bot_colour), '500px')
    agg_wr_chart = _d(C.scatter('bluff_rate', 'win_rate', 'Bluff Rate', 'Win Rate',
                                'Does Aggression Pay Off? Bluff Rate vs Win Rate', players, metrics, bot_colour))
    pos_wr_chart = _d(C.scatter('avg_position', 'win_rate', 'Avg Relative Position', 'Win Rate',
                                'Position vs Win Rate', players, metrics, bot_colour, '.3f', '.1%'))

    bluff_out = _d(C.by_outcome(
        lambda b: safe_div(b.bluffs, b.play_turns),
        'Bluff Rate by Outcome — do winners bluff more or less?',
        'Bluff Rate', '.1%', players, final_infos), '460px')
    dacc_out  = _d(C.by_outcome(
        lambda b: safe_div(b.successful_doubts, b.doubts),
        'Doubt Accuracy by Outcome — are winners better at catching bluffs?',
        'Doubt Accuracy', '.1%', players, final_infos), '460px')
    drate_out = _d(C.by_outcome(
        lambda b: safe_div(b.doubts, b.not_first_turns),
        'Doubt Rate by Outcome — do winners challenge more or less?',
        'Doubt Rate', '.1%', players, final_infos), '460px')
    cpt_out   = _d(C.by_outcome(
        lambda b: safe_div(b.cards_played, b.play_turns),
        'Cards per Turn by Outcome — do winners play more cards at once?',
        'Avg cards/turn', '.2f', players, final_infos), '460px')

    hm_prev = _d(C.heatmap('prev', players, final_infos), '520px')
    hm_next = _d(C.heatmap('next', players, final_infos), '520px')

    return head('Strategy Guide') + nav(players, bot_colour, 'strategy') + '''
<div class="container-lg py-4">

  <div class="mb-4">
    <h1 class="fw-bold mb-1">📊 Strategy Guide</h1>
    <p class="text-muted lead">
      All cross-bot charts in one place. Use these to understand what winning looks like in Dubito
      and which playing styles dominate.
    </p>
  </div>
''' + f'''
  <!-- Rankings -->
  <section id="rankings" class="mb-5">
    <div class="section-title">Rankings</div>
    <div class="row g-4">
      <div class="col-12">{chart_card(wr_chart)}</div>
      <div class="col-12">{chart_card(outcome_chart,
        'Each bar sums to 100%. Hard Win = 1st place, Soft Win = 2nd–n−2, Loss = last. '
        'Strong bots have a tall green segment.')}</div>
      <div class="col-12">{chart_card(pos_chart,
        'Average relative finish position across all games. '
        'A value above 0.5 means this bot finishes in the top half more often than chance.')}</div>
      <div class="col-12">{chart_card(cards_chart,
        'Winners hold fewer cards when the game ends — they empty their hand faster. '
        'A large gap between "On wins" and "On losses" shows consistent play.')}</div>
    </div>
    {tip_box('The best way to improve at Dubito: finish with fewer cards. '
             'Focus on emptying your hand quickly rather than waiting for the perfect moment.')}
  </section>

  <!-- Behavioral Profiles -->
  <section id="behavior" class="mb-5">
    <div class="section-title">Behavioral Profiles</div>
    <div class="row g-4">
      <div class="col-12">{chart_card(radar_chart,
        'All axes normalized to [0–1]. '
        'Bluff Rate: dishonest plays / play turns. '
        'Bluff Stealth: uncaught bluffs / total bluffs. '
        'Doubt Rate: doubts / eligible turns. '
        'Doubt Accuracy: successful doubts / total doubts. '
        'Cards/Turn: avg cards per play turn (normalized by max).')}</div>
      <div class="col-12 col-xl-6">{chart_card(style_chart,
        'Top-right = plays actively (bluffs and doubts a lot). '
        'Bottom-left = passive play. Most winning bots cluster in the middle.')}</div>
      <div class="col-12 col-xl-6">{chart_card(qual_chart,
        'Top-right = good at both hiding bluffs AND catching others. '
        'This combination is the hallmark of skilled deceptive play.')}</div>
      <div class="col-12 col-xl-6">{chart_card(bubble_chart,
        'Top-right = frequent AND stealthy bluffers. '
        'Bottom-right = reckless (bluffs often but gets caught). '
        'Bubble size = win rate — bigger means more successful.')}</div>
      <div class="col-12">{chart_card(parco_chart,
        'Each line = one bot traced across all metrics. '
        'Drag an axis range to isolate bots that fit a filter. '
        'Look for lines that stay high on Win Rate — trace them back to see which metrics they share.')}</div>
    </div>
    {tip_box('In Dubito, the winning formula combines <em>selective bluffing</em> (not too much, '
             'done stealthily) with <em>accurate doubting</em> (challenging only when suspicious). '
             'Blind aggression or blind trust both lose.')}
  </section>

  <!-- Strategy Analysis -->
  <section id="strategy" class="mb-5">
    <div class="section-title">Strategy Analysis</div>
    <div class="row g-4">
      <div class="col-12 col-xl-6">{chart_card(agg_wr_chart,
        'Does bluffing more often lead to winning? '
        'An upward trend means aggression pays; a flat or downward trend means it backfires.')}</div>
      <div class="col-12 col-xl-6">{chart_card(pos_wr_chart,
        'Sanity check: win rate and finish position should correlate strongly. '
        'Outliers here signal interesting edge cases.')}</div>
      <div class="col-12">{chart_card(bluff_out,
        'Compare bluff rates across outcomes. '
        'If the Hard Win bar is consistently higher than the Loss bar, bluffing helps win.')}</div>
      <div class="col-12">{chart_card(dacc_out,
        'Do bots doubt more accurately in games they win? '
        'A gap between Hard Win and Loss reveals whether doubt quality drives outcomes.')}</div>
      <div class="col-12">{chart_card(drate_out,
        'Do winners challenge more or less than they do in losing games? '
        'Selective doubters (lower doubt rate in wins) pick better spots.')}</div>
      <div class="col-12">{chart_card(cpt_out,
        'Do winners play more cards per turn? Finishing fast requires playing large sets, '
        'but playing too aggressively invites challenges.')}</div>
    </div>
    {tip_box('Key takeaway: it is not <em>how much</em> you doubt that matters — it is <em>how accurately</em>. '
             'Doubting blindly forces opponents to pick up cards randomly, '
             'but missing doubts lets bluffers accumulate advantages.')}
  </section>

  <!-- Head-to-Head -->
  <section id="h2h" class="mb-5">
    <div class="section-title">Head-to-Head</div>
    <p class="text-muted small mb-3">
      Win rate of the <strong>row bot</strong> when the <strong>column bot</strong> is its adjacent neighbor.
      Green = advantage, red = disadvantage.
    </p>
    <div class="row g-4">
      <div class="col-12 col-xl-6">{chart_card(hm_prev,
        'Win rate when the column bot sits immediately before you in turn order.')}</div>
      <div class="col-12 col-xl-6">{chart_card(hm_next,
        'Win rate when the column bot sits immediately after you in turn order.')}</div>
    </div>
    {tip_box('In Dubito, seat position matters. '
             'Sitting after a heavy bluffer forces you to decide on their plays — '
             'use the charts above to spot which neighbors give you the best odds.')}
  </section>

</div>
''' + foot(generated)


def _page_compare(players, metrics, bot_colour, generated) -> str:
    players_json  = json.dumps(players)
    colours_json  = json.dumps(bot_colour)
    metrics_json  = json.dumps(metrics)

    checkboxes = ''.join(
        f'<label class="bot-cb-label" style="border-color:{bot_colour[b]};color:{bot_colour[b]};">'
        f'<input class="bot-cb" type="checkbox" value="{b}" checked hidden>{b}'
        f'</label>'
        for b in players
    )

    compare_js = f'''
<script>
const PLAYERS  = {players_json};
const COLOURS  = {colours_json};
const METRICS  = {metrics_json};

const PCT_KEYS = ['win_rate','hard_win_rate','soft_win_rate','loss_rate',
                  'bluff_rate','bluff_stealth','doubt_rate','doubt_accuracy'];
const ALL_KEYS = [...PCT_KEYS, 'avg_position','cards_per_turn'];
const ALL_LABELS = {{
  win_rate:'Win Rate', hard_win_rate:'Hard Win %', soft_win_rate:'Soft Win %',
  loss_rate:'Loss Rate', bluff_rate:'Bluff Rate', bluff_stealth:'Bluff Stealth',
  doubt_rate:'Doubt Rate', doubt_accuracy:'Doubt Accuracy',
  avg_position:'Avg Position', cards_per_turn:'Cards/Turn',
}};

function fmt(val, key) {{
  return PCT_KEYS.includes(key) ? (val*100).toFixed(1)+'%' : val.toFixed(2);
}}

function selected() {{
  return [...document.querySelectorAll('.bot-cb:checked')].map(c => c.value);
}}

const PLOTLY_LAYOUT = {{
  paper_bgcolor:'white', plot_bgcolor:'white',
  font:{{family:'Inter, sans-serif'}},
  legend:{{orientation:'h', y:1.08, x:0}},
  margin:{{t:20, b:60, l:40, r:20}},
}};

function renderRadar(sel) {{
  const axes = ['Win Rate','Bluff Rate','Bluff Stealth','Doubt Rate','Doubt Accuracy','Cards/Turn'];
  const keys = ['win_rate','bluff_rate','bluff_stealth','doubt_rate','doubt_accuracy','cards_per_turn'];
  const maxCpt = Math.max(...PLAYERS.map(b => METRICS[b].cards_per_turn)) || 1;
  const closed = [...axes, axes[0]];
  const data = sel.map(b => {{
    const m = METRICS[b];
    const vals = keys.map(k => k === 'cards_per_turn' ? m[k] / maxCpt : m[k]);
    return {{
      type:'scatterpolar', name:b,
      r:[...vals, vals[0]], theta:closed,
      fill:'toself', line:{{color:COLOURS[b]}},
      fillcolor:COLOURS[b], opacity:0.2,
    }};
  }});
  Plotly.react('cmp-radar', data, {{
    ...PLOTLY_LAYOUT,
    polar:{{radialaxis:{{visible:true, range:[0,1], tickformat:'.0%'}}}},
    margin:{{t:20, b:40, l:60, r:180}}, height:420,
  }}, {{responsive:true}});
}}

function renderOutcome(sel) {{
  const data = sel.map(b => {{
    const m = METRICS[b];
    const ys = [m.hard_win_rate, m.soft_win_rate, m.loss_rate];
    return {{
      type:'bar', name:b,
      x:['Hard Win','Soft Win','Loss'], y:ys,
      marker:{{color:COLOURS[b]}},
      text:ys.map(v => (v*100).toFixed(1)+'%'), textposition:'outside',
    }};
  }});
  Plotly.react('cmp-outcome', data, {{
    ...PLOTLY_LAYOUT,
    barmode:'group', yaxis:{{tickformat:'.0%'}},
    height:360,
  }}, {{responsive:true}});
}}

function renderMetrics(sel) {{
  const metKeys = ['bluff_rate','bluff_stealth','doubt_rate','doubt_accuracy'];
  const metLabels = ['Bluff Rate','Bluff Stealth','Doubt Rate','Doubt Accuracy'];
  const data = sel.map(b => {{
    const m = METRICS[b];
    return {{
      type:'bar', name:b,
      x:metLabels, y:metKeys.map(k => m[k]),
      marker:{{color:COLOURS[b]}},
      text:metKeys.map(k => (m[k]*100).toFixed(1)+'%'), textposition:'outside',
    }};
  }});
  Plotly.react('cmp-metrics', data, {{
    ...PLOTLY_LAYOUT,
    barmode:'group', yaxis:{{tickformat:'.0%'}},
    height:360,
  }}, {{responsive:true}});
}}

function renderTable(sel) {{
  if (!sel.length) {{ document.getElementById('cmp-table').innerHTML = ''; return; }}
  let html = '<div class="table-responsive"><table class="table table-bordered align-middle bg-white mb-0"><thead><tr><th>Metric</th>';
  for (const b of sel) html += `<th style="color:${{COLOURS[b]}}">${{b}}</th>`;
  html += '</tr></thead><tbody>';
  for (const k of ALL_KEYS) {{
    const best = sel.reduce((a, b) =>
      k === 'loss_rate' ? (METRICS[a][k] < METRICS[b][k] ? a : b)
                        : (METRICS[a][k] > METRICS[b][k] ? a : b), sel[0]);
    html += `<tr><td class="text-muted small">${{ALL_LABELS[k]}}</td>`;
    for (const b of sel) {{
      const isBest = b === best && sel.length > 1;
      html += `<td class="text-end fw-semibold" style="${{isBest ? 'background:#e8f5e9' : ''}}">${{fmt(METRICS[b][k], k)}}</td>`;
    }}
    html += '</tr>';
  }}
  html += '</tbody></table></div>';
  document.getElementById('cmp-table').innerHTML = html;
}}

function updateAll() {{
  const sel = selected();
  renderRadar(sel);
  renderOutcome(sel);
  renderMetrics(sel);
  renderTable(sel);
}}

document.addEventListener('DOMContentLoaded', () => {{
  updateAll();
  document.querySelectorAll('.bot-cb').forEach(cb => cb.addEventListener('change', updateAll));
  document.getElementById('select-all').addEventListener('click', () => {{
    document.querySelectorAll('.bot-cb').forEach(c => c.checked = true);
    updateAll();
  }});
  document.getElementById('select-none').addEventListener('click', () => {{
    document.querySelectorAll('.bot-cb').forEach(c => c.checked = false);
    updateAll();
  }});
}});
</script>
'''

    return head('Compare Bots') + nav(players, bot_colour, 'compare') + f'''
<div class="container-lg py-4">

  <div class="mb-4">
    <h1 class="fw-bold mb-1">⚖️ Compare Bots</h1>
    <p class="text-muted lead">Select the bots you want to compare. All charts update instantly.</p>
  </div>

  <!-- Bot selector -->
  <div class="chart-card mb-4">
    <div class="d-flex align-items-center gap-3 mb-2">
      <span class="fw-semibold small">Select bots:</span>
      <button id="select-all"  class="btn btn-sm btn-outline-secondary">All</button>
      <button id="select-none" class="btn btn-sm btn-outline-secondary">None</button>
    </div>
    <div class="d-flex flex-wrap gap-2">{checkboxes}</div>
  </div>

  <!-- Stats table -->
  <div class="chart-card mb-4">
    <div class="section-title mb-3">Stats Table</div>
    <p class="text-muted small mb-2">Best value in each row is highlighted green.</p>
    <div id="cmp-table"></div>
  </div>

  <!-- Charts -->
  <div class="row g-4">
    <div class="col-12">
      <div class="chart-card">
        <div class="section-title mb-2">Behavioral Fingerprint</div>
        <div id="cmp-radar" style="width:100%;height:420px;"></div>
      </div>
    </div>
    <div class="col-12 col-xl-6">
      <div class="chart-card">
        <div class="section-title mb-2">Outcome Distribution</div>
        <p class="text-muted small mb-0">Hard Win = 1st place, Soft Win = 2nd–n−2, Loss = last.</p>
        <div id="cmp-outcome" style="width:100%;height:360px;"></div>
      </div>
    </div>
    <div class="col-12 col-xl-6">
      <div class="chart-card">
        <div class="section-title mb-2">Behavioral Metrics</div>
        <p class="text-muted small mb-0">Side-by-side comparison of bluffing and doubting profiles.</p>
        <div id="cmp-metrics" style="width:100%;height:360px;"></div>
      </div>
    </div>
  </div>

</div>
{compare_js}
''' + foot(generated)


def _page_bot(bot, rank, players, final_infos, metrics, bot_colour,
              baselines, generated) -> str:
    hard_base, soft_base, win_base = baselines
    info   = final_infos[bot]
    m      = metrics[bot]
    colour = bot_colour[bot]
    hwr    = m['hard_win_rate']
    swr    = m['soft_win_rate']
    lr     = m['loss_rate']

    perf_cards = f'''
<div class="row g-2 mb-3">
  <div class="col-6 col-md-2">{stat_card(f"{info.total.games:,}", "Total games")}</div>
  <div class="col-6 col-md-2">{stat_card(f"{hwr:.1%}", "Hard Win %", colour, hwr)}</div>
  <div class="col-6 col-md-2">{stat_card(f"{(hwr-hard_base):+.1%}", "vs Hard Baseline",
                                          "#198754" if hwr >= hard_base else "#dc3545")}</div>
  <div class="col-6 col-md-2">{stat_card(f"{swr:.1%}", "Soft Win %", "#0d6efd", swr)}</div>
  <div class="col-6 col-md-2">{stat_card(f"{(swr-soft_base):+.1%}", "vs Soft Baseline",
                                          "#198754" if swr >= soft_base else "#dc3545")}</div>
  <div class="col-6 col-md-2">{stat_card(f"{lr:.1%}", "Loss Rate", "#dc3545")}</div>
</div>'''

    beh_cards = f'''
<div class="row g-2 mb-4">
  <div class="col-6 col-md-3">{stat_card(f"{m['bluff_rate']:.1%}", "Bluff Rate")}</div>
  <div class="col-6 col-md-3">{stat_card(f"{m['bluff_stealth']:.1%}", "Bluff Stealth")}</div>
  <div class="col-6 col-md-3">{stat_card(f"{m['doubt_rate']:.1%}", "Doubt Rate")}</div>
  <div class="col-6 col-md-3">{stat_card(f"{m['doubt_accuracy']:.1%}", "Doubt Accuracy")}</div>
  <div class="col-6 col-md-3">{stat_card(f"{m['cards_per_turn']:.2f}", "Cards per Turn")}</div>
  <div class="col-6 col-md-3">{stat_card(f"{info.losses.avg_cards:.2f}", "Avg cards on loss", "#dc3545")}</div>
  <div class="col-6 col-md-3">{stat_card(f"{info.hard_wins.avg_cards:.2f}", "Avg cards on win", colour)}</div>
  <div class="col-6 col-md-3">{stat_card(f"{m['avg_position']:.3f}", "Avg relative position")}</div>
</div>'''

    prev_chart = div(C.neighbor_bar(bot, 'prev', players, final_infos, bot_colour), '320px')
    next_chart = div(C.neighbor_bar(bot, 'next', players, final_infos, bot_colour), '320px')

    sc1 = div(C.scatter_highlight('bluff_rate', 'win_rate', 'Bluff Rate', 'Win Rate',
                                  f'{bot} — Bluff Rate vs Win Rate',
                                  players, metrics, bot_colour, bot), '380px')
    sc2 = div(C.scatter_highlight('bluff_stealth', 'doubt_accuracy', 'Bluff Stealth', 'Doubt Accuracy',
                                  f'{bot} — Bluff Stealth vs Doubt Accuracy',
                                  players, metrics, bot_colour, bot), '380px')

    prev_next = ', '.join(
        f'<a href="{players[i]}.html" style="color:{bot_colour[players[i]]};font-weight:600">{players[i]}</a>'
        for i in [players.index(bot) - 1, (players.index(bot) + 1) % len(players)]
        if players[i] != bot
    )

    return head(bot, extra_css=f'.hero-dot{{background:{colour}}}') + nav(players, bot_colour, 'bot', prefix='../') + f'''
<div class="container-lg py-4">

  <!-- Hero -->
  <div class="card mb-4 shadow-sm" style="border-left:5px solid {colour};">
    <div class="card-body d-flex align-items-center gap-4">
      <div style="width:56px;height:56px;border-radius:50%;background:{colour};flex-shrink:0;"></div>
      <div>
        <h2 class="fw-bold mb-0">{bot}</h2>
        <span class="text-muted">Rank #{rank} of {len(players)}</span>
      </div>
      <div class="ms-auto d-flex gap-2 flex-wrap">
        <span class="badge fs-6" style="background:{colour};">{hwr:.1%} hard win</span>
        <span class="badge fs-6 bg-primary">{swr:.1%} soft win</span>
        <span class="badge fs-6 bg-danger">{lr:.1%} loss</span>
      </div>
    </div>
  </div>

  <!-- Performance stats -->
  <section class="mb-4">
    <div class="section-title">Performance</div>
    {perf_cards}
  </section>

  <!-- Behavioral stats -->
  <section class="mb-4">
    <div class="section-title">Behavioral Profile</div>
    {beh_cards}
  </section>

  <!-- How to play against this bot -->
  <section class="mb-5">
    <div class="section-title">How to Play Against {bot}</div>
    <div class="chart-card">
      {_bot_tips(bot, metrics)}
    </div>
  </section>

  <!-- Neighbor analysis -->
  <section class="mb-5">
    <div class="section-title">Neighbor Analysis</div>
    <p class="text-muted small mb-3">
      Win rate of <strong>{bot}</strong> depending on who sits immediately before or after it in turn order.
    </p>
    <div class="row g-3">
      <div class="col-md-6">{chart_card(prev_chart)}</div>
      <div class="col-md-6">{chart_card(next_chart)}</div>
    </div>
  </section>

  <!-- Where this bot sits -->
  <section class="mb-5">
    <div class="section-title">Where {bot} Sits Among All Bots</div>
    <div class="row g-3">
      <div class="col-md-6">{chart_card(sc1, 'Grey = other bots. Coloured = this bot.')}</div>
      <div class="col-md-6">{chart_card(sc2, 'Grey = other bots. Coloured = this bot.')}</div>
    </div>
  </section>

  <!-- Neighbours -->
  <section class="mb-4">
    <div class="section-title">Explore Neighbors</div>
    <p class="text-muted small">
      Ranked neighbors in the leaderboard: {prev_next}.
      <a href="../compare.html" class="ms-2">⚖️ Compare these bots →</a>
    </p>
  </section>

</div>
''' + foot(generated)


# ── Site generator ─────────────────────────────────────────────────────────────

def generate_html_site(final_infos: dict, config: dict, output_dir: str = 'report_site/') -> None:
    players  = sorted(final_infos.keys(), key=lambda b: win_rate(final_infos[b]), reverse=True)
    colours  = make_bot_colours(players)
    metrics  = _all_metrics(players, final_infos)
    ap       = config.get('available_players', [5])
    avg_n    = sum(ap) / len(ap)
    hard_base = 1.0 / avg_n
    soft_base = max(0.0, (avg_n - 3) / avg_n)
    win_base  = hard_base + soft_base
    baselines = (hard_base, soft_base, win_base)
    generated = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')


    bots_dir = os.path.join(output_dir, 'bots')
    os.makedirs(bots_dir, exist_ok=True)

    def _write(path, content):
        with open(os.path.join(output_dir, path), 'w', encoding='utf-8') as f:
            f.write(content)

    _write('index.html',    _page_index(players, final_infos, metrics, colours, baselines, config, generated))
    _write('strategy.html', _page_strategy(players, final_infos, metrics, colours, baselines, config, generated))
    _write('compare.html',  _page_compare(players, metrics, colours, generated))

    for i, bot in enumerate(players):
        _write(f'bots/{bot}.html', _page_bot(bot, i + 1, players, final_infos, metrics, colours, baselines, generated))

    print(f'Site written to {output_dir}  ({len(players) + 3} files)')
