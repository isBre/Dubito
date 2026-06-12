#!/usr/bin/env python3
"""
app.py — Flask web frontend for Dubito.
Run:  python3 app.py
Deps: pip install flask

All game logic lives in web_session.py (also the backend of the static
GitHub Pages build); these routes only translate HTTP to those handlers.
"""
from flask import Flask, jsonify, render_template, request

import web_session as ws

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/bots")
def api_bots():
    payload, status = ws.handle_list_bots()
    return jsonify(payload), status


@app.route("/api/game", methods=["POST"])
def api_create_game():
    payload, status = ws.handle_create_game(request.get_json(force=True) or {})
    return jsonify(payload), status


@app.route("/api/game/<gid>/play", methods=["POST"])
def api_play(gid: str):
    payload, status = ws.handle_play(gid, request.get_json(force=True) or {})
    return jsonify(payload), status


@app.route("/api/game/<gid>/doubt", methods=["POST"])
def api_doubt(gid: str):
    payload, status = ws.handle_doubt(gid)
    return jsonify(payload), status


if __name__ == "__main__":
    app.run(port=5001, debug=True)
