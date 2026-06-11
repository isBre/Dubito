PALETTE = [
    '#4C78A8', '#F58518', '#E45756', '#72B7B2', '#54A24B',
    '#EECA3B', '#B279A2', '#FF9DA7', '#9D755D', '#BAB0AC',
    '#FF7F0E', '#2CA02C', '#D62728', '#9467BD',
]

LAYOUT_BASE = dict(plot_bgcolor='white', paper_bgcolor='white', font_family='Inter, sans-serif')


def make_bot_colours(players: list) -> dict:
    return {b: PALETTE[i % len(PALETTE)] for i, b in enumerate(players)}


def div(fig, height: str = '420px', div_id: str = '') -> str:
    kw = dict(full_html=False, include_plotlyjs=False, config={'responsive': True})
    if div_id:
        kw['div_id'] = div_id
    return f'<div style="width:100%;height:{height};">{fig.to_html(**kw)}</div>'


_CSS = '''
body{font-family:"Inter",system-ui,sans-serif;background:#f8f9fa}
.navbar-brand{font-weight:700;letter-spacing:.5px}
.nav-link{color:rgba(255,255,255,.65)!important;font-size:.875rem;padding:.3rem .6rem!important}
.nav-link:hover,.nav-link.active{color:#fff!important}
.dropdown-item{font-size:.875rem}
section{scroll-margin-top:70px}
.stat-card{background:#fff;border:1px solid #e9ecef;border-radius:8px;padding:12px 16px;text-align:center;height:100%}
.stat-value{font-size:1.35rem;font-weight:700}
.stat-label{font-size:.72rem;color:#6c757d;text-transform:uppercase;letter-spacing:.5px;margin-top:2px}
.chart-card{background:#fff;border:1px solid #e9ecef;border-radius:10px;padding:16px}
table thead th{background:#343a40;color:#fff;white-space:nowrap}
.section-title{font-size:1.35rem;font-weight:700;border-left:4px solid #4C78A8;padding-left:12px;margin-bottom:.4rem}
.config-badge{display:inline-block;background:#e9ecef;border-radius:20px;padding:4px 14px;font-size:.85rem;font-weight:600;margin:2px}
.tip-box{background:#fff8e1;border-left:4px solid #EECA3B;border-radius:6px;padding:12px 16px;font-size:.88rem}
.nav-card{border:1px solid #e9ecef;border-radius:12px;padding:20px;background:#fff;text-decoration:none;color:inherit;display:block;transition:box-shadow .15s,transform .15s}
.nav-card:hover{box-shadow:0 4px 16px rgba(0,0,0,.1);transform:translateY(-2px);color:inherit}
.bot-cb-label{display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border-radius:20px;border:2px solid;cursor:pointer;font-size:.82rem;font-weight:600;user-select:none;transition:opacity .15s}
.bot-cb-label:has(input:not(:checked)){opacity:.4}
'''


def head(title: str, extra_css: str = '') -> str:
    return f'''<!DOCTYPE html>
<html lang="en" data-bs-theme="light">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{title} — Dubito</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet"/>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>{_CSS}{extra_css}</style>
</head>
<body>'''


def nav(players: list, bot_colour: dict, active: str, prefix: str = '') -> str:
    def _link(href, label, page_id):
        cls = 'nav-link active fw-semibold' if active == page_id else 'nav-link'
        return f'<li class="nav-item"><a class="{cls}" href="{prefix}{href}">{label}</a></li>'

    bot_items = ''.join(
        f'<li><a class="dropdown-item" href="{prefix}bots/{b}.html">'
        f'<span style="display:inline-block;width:9px;height:9px;border-radius:50%;'
        f'background:{bot_colour[b]};margin-right:7px;"></span>{b}</a></li>'
        for b in players
    )
    dd_cls = 'nav-link dropdown-toggle active fw-semibold' if active == 'bot' else 'nav-link dropdown-toggle'
    return f'''
<nav class="navbar navbar-dark bg-dark sticky-top px-4">
  <a class="navbar-brand" href="{prefix}index.html">🎴 Dubito</a>
  <ul class="navbar-nav flex-row gap-1 d-none d-md-flex align-items-center">
    {_link("index.html",    "Overview", "overview")}
    {_link("strategy.html", "Strategy", "strategy")}
    {_link("compare.html",  "Compare",  "compare")}
    <li class="nav-item dropdown">
      <a class="{dd_cls}" href="#" role="button" data-bs-toggle="dropdown">Bots</a>
      <ul class="dropdown-menu dropdown-menu-dark" style="max-height:70vh;overflow-y:auto">{bot_items}</ul>
    </li>
  </ul>
</nav>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>'''


def foot(generated: str) -> str:
    return f'''
<footer class="text-center text-muted py-3 border-top small mt-5">
  Dubito Bot Report &mdash; {generated}
</footer>
</body>
</html>'''


def stat_card(value: str, label: str, colour: str = '',
              progress: float = 0.0, delta: str = '') -> str:
    val_style = f'style="color:{colour};"' if colour else ''
    prog = (
        f'<div class="progress mt-1" style="height:4px;">'
        f'<div class="progress-bar" style="width:{int(progress*100)}%;background:{colour or "#6c757d"};"></div>'
        f'</div>'
    ) if progress else ''
    dt = f'<div class="small mt-1" style="color:{"#198754" if delta.startswith("+") else "#dc3545"}">{delta}</div>' if delta else ''
    return (
        f'<div class="stat-card">'
        f'<div class="stat-value" {val_style}>{value}</div>'
        f'<div class="stat-label">{label}</div>'
        f'{prog}{dt}'
        f'</div>'
    )


def chart_card(fig_html: str, caption: str = '') -> str:
    cap = f'<p class="text-muted small mt-2 mb-0 text-center">{caption}</p>' if caption else ''
    return f'<div class="chart-card">{fig_html}{cap}</div>'


def tip_box(text: str) -> str:
    return f'<div class="tip-box mt-3">💡 {text}</div>'
