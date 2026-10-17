#!/usr/bin/env python3
"""Nic's 5 Nips - local static server with simple HTTP basic auth.

Serves the public/ folder with one shared credential so only Iain gets in.
This site is deliberately kept out of any work tooling; it is a private gift.

Two homes: the Mac (127.0.0.1 behind the cloudflared tunnel) and, from 24 Sep
2026, the Hetzner apps box in a container. Set BIND=0.0.0.0 in the container.

Open house (no password) happens if EITHER:
  - the OPEN-UNTIL file holds a future timestamp (open-day.sh, Mac), or
  - now is inside the OPEN_FROM..OPEN_UNTIL window from the environment.
The window is how the wedding day works on the server: it opens and re-locks
itself with nobody at a keyboard. Anything missing or malformed = locked.
"""
import base64
import datetime
import json
import os
import re
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("NICKS_PORT", "8104"))
HERE = os.path.dirname(os.path.abspath(__file__))
WEBROOT = os.path.join(HERE, "public")

USERNAME = os.environ.get("NICKS_USER", "iain")
PASSWORD = os.environ.get("NICKS_PASS", "iains5nips")
REALM = "Nic's 5 Nips"
_EXPECTED = "Basic " + base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()

# Open-house flag. Holds a local ISO timestamp; while that time is in the
# future the site serves with no password at all (for Nic's wedding day).
# Read on every request, so open-day.sh can open and shut the door without a
# restart, and so it re-locks itself the moment the timestamp passes.
# Anything missing, unreadable or malformed counts as locked - it fails shut.
OPEN_FLAG = os.environ.get("OPEN_FLAG", os.path.join(HERE, "OPEN-UNTIL"))
OPEN_FROM_ENV = os.environ.get("OPEN_FROM", "")
OPEN_UNTIL_ENV = os.environ.get("OPEN_UNTIL", "")


def _parse(value):
    try:
        return datetime.datetime.fromisoformat(value.strip())
    except (AttributeError, ValueError):
        return None


def open_window():
    """True while now is inside OPEN_FROM..OPEN_UNTIL. Fails shut."""
    start, end = _parse(OPEN_FROM_ENV), _parse(OPEN_UNTIL_ENV)
    if not start or not end:
        return False
    return start <= datetime.datetime.now() < end


def open_house():
    if open_window():
        return True
    try:
        with open(OPEN_FLAG) as fh:
            until = _parse(fh.read())
    except OSError:
        return False
    return bool(until) and datetime.datetime.now() < until


# NicAttack's shared high score board: one JSON file, outside public/, so
# Iain, Nic and Paul all see the same table. Only reachable behind the login.
SCORES_FILE = os.environ.get("SCORES_FILE", os.path.join(HERE, "data", "nicattack-scores.json"))
SCORES_PATH = "/api/nicattack/scores"
_scores_lock = threading.Lock()


def load_scores():
    try:
        with open(SCORES_FILE) as fh:
            rows = json.load(fh)
        return rows if isinstance(rows, list) else []
    except (OSError, ValueError):
        return []


def add_score(entry):
    """Validate, insert, keep the best 100, write atomically. Returns (rows, rank)."""
    name = re.sub(r"[^A-Z0-9 .!'-]", "", str(entry.get("name", "")).upper()).strip()[:10]
    score, wave, start = entry.get("score"), entry.get("wave"), entry.get("start", 1)
    if not name or not all(isinstance(v, int) and not isinstance(v, bool) for v in (score, wave, start)):
        raise ValueError("bad entry")
    if not (0 < score < 100000000 and 0 < wave < 1000 and 0 < start <= wave):
        raise ValueError("out of range")
    row = {"name": name, "score": score, "wave": wave, "start": start,
           "date": datetime.date.today().isoformat()}
    with _scores_lock:
        rows = load_scores() + [row]
        rows.sort(key=lambda r: -r["score"])
        rows = rows[:100]
        os.makedirs(os.path.dirname(SCORES_FILE), exist_ok=True)
        tmp = SCORES_FILE + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(rows, fh)
        os.replace(tmp, SCORES_FILE)
    rank = next((i + 1 for i, r in enumerate(rows) if r is row), None)
    return rows, rank


class AuthHandler(SimpleHTTPRequestHandler):
    def _json(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _challenge(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", f'Basic realm="{REALM}"')
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h1>401 - Restricted</h1>")

    def _authed(self):
        if open_house():
            return True
        return self.headers.get("Authorization", "") == _EXPECTED

    def do_GET(self):
        if not self._authed():
            return self._challenge()
        if self.path.split("?")[0] == SCORES_PATH:
            return self._json(200, {"scores": load_scores()[:20]})
        return super().do_GET()

    def do_POST(self):
        if not self._authed():
            return self._challenge()
        if self.path.split("?")[0] != SCORES_PATH:
            return self._json(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1024:
                raise ValueError("bad length")
            rows, rank = add_score(json.loads(self.rfile.read(length)))
        except (ValueError, TypeError, AttributeError) as exc:
            return self._json(400, {"error": str(exc)})
        return self._json(200, {"scores": rows[:20], "rank": rank})

    def do_HEAD(self):
        if not self._authed():
            return self._challenge()
        return super().do_HEAD()


if __name__ == "__main__":
    handler = partial(AuthHandler, directory=WEBROOT)
    bind = os.environ.get("BIND", "127.0.0.1")
    httpd = ThreadingHTTPServer((bind, PORT), handler)
    print(f"Nic's 5 Nips serving {WEBROOT} on {bind}:{PORT}", flush=True)
    httpd.serve_forever()
