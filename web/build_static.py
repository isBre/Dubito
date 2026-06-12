#!/usr/bin/env python3
"""
Build the static, serverless build of the playable Dubito web game.

The Flask app's game logic already lives in flask-free web_session.py, so the
whole engine (rules, bots, session handling) can run in the browser through
Pyodide. This script produces a directory GitHub Pages can serve as-is:

    index.html          templates/index.html with the Pyodide loader injected
    static_backend.js   defines window.dubitoLocalApi over web_session.handle_api
    engine.zip          the pure-Python engine, unpacked into Pyodide's FS

Usage:  python web/build_static.py --out site/play
"""
import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PYODIDE_VERSION = "0.26.4"

# Everything web_session imports, and nothing more (no flask, rl, experiments).
ENGINE_SOURCES = [
    "web_session.py",
    "dubito/*.py",
    "bots/*.py",
    "bots/manual/*.py",
    "bots/llms/*.py",
    "machine_learning/dataset.py",
]


def build(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out_dir / "engine.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for pattern in ENGINE_SOURCES:
            paths = sorted(ROOT.glob(pattern))
            if not paths:
                raise FileNotFoundError(f"engine source pattern matched nothing: {pattern}")
            for path in paths:
                zf.write(path, path.relative_to(ROOT))

    html = (ROOT / "templates" / "index.html").read_text()
    marker = "<script>"
    if html.count(marker) != 1:
        raise ValueError(
            f"expected exactly one inline {marker} in templates/index.html, "
            f"found {html.count(marker)} — update the injection logic"
        )
    inject = (
        f'<script src="https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/pyodide.js"></script>\n'
        f'<script src="static_backend.js"></script>\n'
        f"{marker}"
    )
    (out_dir / "index.html").write_text(html.replace(marker, inject))

    (out_dir / "static_backend.js").write_text((ROOT / "web" / "static_backend.js").read_text())

    sizes = {p.name: p.stat().st_size for p in sorted(out_dir.iterdir())}
    print(f"static game built in {out_dir}:")
    for name, size in sizes.items():
        print(f"  {name:20} {size:>8,} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="site/play", type=Path,
                        help="output directory (default: site/play)")
    build(parser.parse_args().out)
