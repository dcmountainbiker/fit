"""One-shot Strava OAuth helper.

Starts a local HTTP listener, prints the authorize URL, waits for the redirect
with the auth code, exchanges it for tokens, and writes them back to
~/.config/fit/strava.env.

Usage:
    python3 src/strava_oauth.py
"""

from __future__ import annotations

import http.server
import os
import socketserver
import sys
import urllib.parse
import urllib.request
import json
from pathlib import Path

ENV_PATH = Path.home() / ".config" / "fit" / "strava.env"
PORT = 8721
REDIRECT_URI = f"http://localhost:{PORT}/callback"
SCOPES = "read,activity:read_all,profile:read_all"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def save_env(env: dict[str, str]) -> None:
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENV_PATH.write_text("".join(f"{k}={v}\n" for k, v in env.items()))
    os.chmod(ENV_PATH, 0o600)


def authorize_url(client_id: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": SCOPES,
    }
    return "https://www.strava.com/oauth/authorize?" + urllib.parse.urlencode(params)


def exchange_code(client_id: str, client_secret: str, code: str) -> dict:
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(
        "https://www.strava.com/oauth/token",
        data=data,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


class _Handler(http.server.BaseHTTPRequestHandler):
    code_holder: dict[str, str] = {}

    def log_message(self, *a, **k):  # quiet
        pass

    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        if "error" in qs:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"Strava returned error: {qs['error'][0]}".encode())
            _Handler.code_holder["error"] = qs["error"][0]
            return
        code = qs.get("code", [None])[0]
        scope = qs.get("scope", [""])[0]
        if not code:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"missing code")
            return
        _Handler.code_holder["code"] = code
        _Handler.code_holder["scope"] = scope
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"""<html><body style="font-family:system-ui;padding:2em;color:#2F4858">
        <h2>Connected.</h2><p>You can close this tab.</p></body></html>""")


def main() -> int:
    env = load_env()
    client_id = env.get("STRAVA_CLIENT_ID")
    client_secret = env.get("STRAVA_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("Missing STRAVA_CLIENT_ID or STRAVA_CLIENT_SECRET in", ENV_PATH)
        return 1

    url = authorize_url(client_id)
    print()
    print("Open this URL in a browser on this machine:")
    print()
    print(url)
    print()
    print(f"Listening on {REDIRECT_URI} ...")

    with socketserver.TCPServer(("127.0.0.1", PORT), _Handler) as httpd:
        httpd.timeout = 300
        # Handle a few requests; first /callback wins.
        while "code" not in _Handler.code_holder and "error" not in _Handler.code_holder:
            httpd.handle_request()

    if "error" in _Handler.code_holder:
        print("OAuth error:", _Handler.code_holder["error"])
        return 1

    code = _Handler.code_holder["code"]
    scope = _Handler.code_holder.get("scope", "")
    print(f"Got code. Scope granted: {scope}")
    print("Exchanging for tokens...")

    tokens = exchange_code(client_id, client_secret, code)
    if "access_token" not in tokens:
        print("Token exchange failed:", json.dumps(tokens, indent=2))
        return 1

    env["STRAVA_ACCESS_TOKEN"] = tokens["access_token"]
    env["STRAVA_REFRESH_TOKEN"] = tokens["refresh_token"]
    env["STRAVA_TOKEN_EXPIRES_AT"] = str(tokens["expires_at"])
    env["STRAVA_SCOPE"] = scope
    save_env(env)
    print(f"Saved new tokens to {ENV_PATH}")
    athlete = tokens.get("athlete", {})
    print(f"Authorized as: {athlete.get('firstname','?')} {athlete.get('lastname','')} (id {athlete.get('id')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
