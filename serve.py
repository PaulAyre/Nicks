#!/usr/bin/env python3
"""Nic's 5 Nips - local static server with simple HTTP basic auth.

Serves the public/ folder on 127.0.0.1 only (reachable from the outside
solely through the cloudflared tunnel at nicks.paulayre.co.uk). One shared
credential so only Iain gets in. This site is deliberately kept off Render
and out of any work/personal tooling - it is a private gift for a friend.
"""
import base64
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


class AuthHandler(SimpleHTTPRequestHandler):
    def _challenge(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", f'Basic realm="{REALM}"')
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h1>401 - Restricted</h1>")

    def _authed(self):
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
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    print(f"Nic's 5 Nips serving {WEBROOT} on 127.0.0.1:{PORT}")
    httpd.serve_forever()
