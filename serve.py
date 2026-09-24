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
import os
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


class AuthHandler(SimpleHTTPRequestHandler):
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
        return super().do_GET()

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
