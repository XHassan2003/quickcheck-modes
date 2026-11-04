"""
QuickCheck Modes - give a link, choose Functional, UI or Both.

    python app.py      -> http://localhost:8080   (PORT=xxxx to change)
"""
import json
import os
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from modes.runner import Job

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
app = Flask(__name__, static_folder=None)
app.json.sort_keys = False
LIVE = {}


@app.get("/")
def index():
    return send_from_directory(ROOT / "ui", "index.html")


@app.post("/api/test")
def start():
    b = request.get_json(silent=True) or {}
    url, mode = (b.get("url") or "").strip(), b.get("mode", "both")
    if not url:
        return jsonify(error="Enter a link first."), 400
    if mode not in ("functional", "ui", "both"):
        return jsonify(error="Choose Functional, UI or Both."), 400
    jid = uuid.uuid4().hex[:8]
    job = Job(url, mode, bool(b.get("linked")), max(1, min(int(b.get("max_pages") or 6), 25)), RESULTS / jid)
    LIVE[jid] = job
    job.save()

    def work():
        job.run()
        LIVE.pop(jid, None)

    threading.Thread(target=work, daemon=True).start()
    return jsonify(id=jid), 202


@app.get("/api/test/<jid>")
def get(jid):
    if jid in LIVE:
        return jsonify(LIVE[jid].state)
    f = RESULTS / jid / "result.json"
    return (jsonify(json.loads(f.read_text(encoding="utf-8"))), 200) if f.exists() else (jsonify(error="Not found"), 404)


@app.get("/api/tests")
def history():
    out = []
    for f in sorted(RESULTS.glob("*/result.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:15]:
        s = json.loads(f.read_text(encoding="utf-8"))
        out.append({k: s.get(k) for k in ("id", "url", "mode", "status", "started", "summary")})
    return jsonify(out)


@app.get("/results/<jid>/<path:name>")
def files(jid, name):
    return send_from_directory(RESULTS / jid, name)


@app.get("/demo/")
@app.get("/demo/<path:name>")
def practice(name="index.html"):
    if "." not in name.rsplit("/", 1)[-1]:
        name = name.rstrip("/") + ".html"
    return send_from_directory(ROOT / "practice_site", name)


if __name__ == "__main__":
    RESULTS.mkdir(exist_ok=True)
    port = int(os.environ.get("PORT", 8080))
    print(f"\n  QuickCheck Modes:  http://localhost:{port}\n  Practice site:     http://localhost:{port}/demo\n")
    app.run(host="127.0.0.1", port=port, threaded=True)
