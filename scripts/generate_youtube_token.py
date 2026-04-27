#!/usr/bin/env python3
"""
generate_youtube_token.py — One-time OAuth 2.0 token setup for YouTube Data API v3.

Run this ONCE locally to authorize the IRON STATIC YouTube account. It opens a browser
for the Google OAuth consent screen, captures the authorization code, and exchanges it
for a refresh token. The refresh token is printed to stdout so you can add it to
GitHub Actions secrets and your local .env.

This script is NOT for CI. Run it locally, capture the token, then use post_youtube.py
for all actual uploads (which uses the refresh token to obtain short-lived access tokens
without any browser interaction).

Setup (one time):
  1. Create a project in Google Cloud Console: https://console.cloud.google.com/
  2. Enable the YouTube Data API v3.
  3. Create an OAuth 2.0 Client ID (type: Desktop app).
  4. Download the client secret JSON → credentials/youtube_client_secret.json
     (this file is .gitignored — never commit it)
  5. Run: python scripts/generate_youtube_token.py

Required scopes:
  https://www.googleapis.com/auth/youtube.upload
  https://www.googleapis.com/auth/youtube.readonly

After running:
  - Add YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN
    as GitHub Actions repository secrets.
  - They will be offered for automatic append to your local .env.

Usage:
  python scripts/generate_youtube_token.py
  python scripts/generate_youtube_token.py --client-secret credentials/youtube_client_secret.json
  python scripts/generate_youtube_token.py --check            # verify existing token works
"""

import argparse
import http.server
import json
import logging
import os
import sys
import threading
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CLIENT_SECRET_PATH = REPO_ROOT / "credentials" / "youtube_client_secret.json"

OAUTH_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"


# ---------------------------------------------------------------------------
# Shared: write to .env
# ---------------------------------------------------------------------------

def _offer_env_write(env_file: Path, client_id: str, client_secret: str, refresh_token: str) -> None:
    if not env_file.exists():
        log.info("No .env file at %s. Create one and add the keys above.", env_file)
        return

    existing = env_file.read_text()
    lines_to_add = []
    for key, val in [
        ("YOUTUBE_CLIENT_ID", client_id),
        ("YOUTUBE_CLIENT_SECRET", client_secret),
        ("YOUTUBE_REFRESH_TOKEN", refresh_token),
    ]:
        if key not in existing:
            lines_to_add.append(f"{key}={val}")

    if lines_to_add:
        answer = input(
            f"Append {len(lines_to_add)} YouTube keys to {env_file}? [y/N] "
        ).strip().lower()
        if answer == "y":
            with open(env_file, "a") as f:
                f.write("\n# YouTube Data API v3\n")
                for line in lines_to_add:
                    f.write(line + "\n")
            log.info("Appended to %s.", env_file)
        else:
            log.info("Skipped .env update. Copy values manually from above.")
    else:
        log.info("YouTube keys already present in %s.", env_file)


# ---------------------------------------------------------------------------
# OAuth browser flow
# ---------------------------------------------------------------------------

def _load_client_secret(path: Path) -> tuple[str, str]:
    """Load client_id and client_secret from a downloaded OAuth client secret JSON."""
    if not path.exists():
        log.error("Client secret file not found: %s", path)
        log.error(
            "Download it from Google Cloud Console → APIs & Services → Credentials "
            "→ your OAuth 2.0 Client ID → Download JSON."
        )
        sys.exit(1)

    with open(path) as f:
        data = json.load(f)

    # Google's client secret JSON wraps credentials under "installed" or "web"
    client_data = data.get("installed") or data.get("web")
    if not client_data:
        log.error("Unexpected client secret format. Expected 'installed' or 'web' key.")
        sys.exit(1)

    client_id = client_data.get("client_id", "")
    client_secret = client_data.get("client_secret", "")

    if not client_id or not client_secret:
        log.error("client_id or client_secret missing from %s", path)
        sys.exit(1)

    return client_id, client_secret


def _build_auth_url(client_id: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",     # required to get a refresh token
        "prompt": "consent",           # force consent screen to always return refresh_token
    }
    return f"{OAUTH_AUTHORIZE_URL}?{urlencode(params)}"


def _exchange_code(code: str, client_id: str, client_secret: str) -> dict:
    """Exchange authorization code for tokens."""
    body = urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()

    req = Request(
        OAUTH_TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Minimal HTTP handler to capture the OAuth redirect."""

    auth_code: str | None = None
    error: str | None = None

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)
        if "error" in params:
            _CallbackHandler.error = params["error"][0]
            self._respond("Authorization denied. You can close this window.")
        elif "code" in params:
            _CallbackHandler.auth_code = params["code"][0]
            self._respond(
                "Authorization successful! IRON STATIC has YouTube access. "
                "You can close this window and return to the terminal."
            )
        else:
            self._respond("Unexpected response. Check terminal output.")

    def _respond(self, message: str) -> None:
        body = f"<html><body><h2>{message}</h2></body></html>".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # suppress server access logs
        pass


def _run_local_server() -> str:
    """Start a local HTTP server, wait for the OAuth callback, return the auth code."""
    server = http.server.HTTPServer(("localhost", REDIRECT_PORT), _CallbackHandler)
    server.timeout = 120  # 2 minutes to complete auth

    log.info("Waiting for OAuth callback on http://localhost:%d/callback ...", REDIRECT_PORT)

    # Serve requests until we have a code or error
    while _CallbackHandler.auth_code is None and _CallbackHandler.error is None:
        server.handle_request()

    server.server_close()

    if _CallbackHandler.error:
        log.error("OAuth error: %s", _CallbackHandler.error)
        sys.exit(1)

    return _CallbackHandler.auth_code


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------

def _check_token(client_id: str, client_secret: str, refresh_token: str) -> None:
    """Exchange refresh token for a new access token and verify it works."""
    log.info("Checking refresh token by requesting a new access token ...")
    body = urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode()

    req = Request(
        OAUTH_TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        log.error("Token refresh failed: %s", exc)
        sys.exit(1)

    if "error" in data:
        log.error("Token error: %s — %s", data.get("error"), data.get("error_description"))
        sys.exit(1)

    access_token = data.get("access_token", "")
    expires_in = data.get("expires_in", 0)
    scope = data.get("scope", "")
    log.info("Token valid. Access token obtained (expires in %ds).", expires_in)
    log.info("Scopes granted: %s", scope)

    required = "https://www.googleapis.com/auth/youtube.upload"
    if required not in scope:
        log.warning("Missing required scope: %s", required)
        log.warning("Re-run generate_youtube_token.py to re-authorize with full scopes.")
    else:
        log.info("youtube.upload scope confirmed.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-time OAuth 2.0 setup for YouTube Data API v3."
    )
    parser.add_argument(
        "--client-secret",
        default=str(DEFAULT_CLIENT_SECRET_PATH),
        help=(
            f"Path to downloaded OAuth client secret JSON "
            f"(default: {DEFAULT_CLIENT_SECRET_PATH})."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Verify that existing YOUTUBE_REFRESH_TOKEN (from env or .env) "
            "is valid and has the required scopes. Does not open a browser."
        ),
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Debug logging.")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load .env from repo root if present
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

    client_secret_path = Path(args.client_secret)

    if args.check:
        # --check mode: verify existing token
        client_id = os.environ.get("YOUTUBE_CLIENT_ID", "")
        client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
        refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")

        if not client_id or not client_secret or not refresh_token:
            # Fall back to client secret file
            if client_secret_path.exists():
                client_id, client_secret = _load_client_secret(client_secret_path)
            else:
                log.error(
                    "Set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN "
                    "in environment or .env, or provide --client-secret path."
                )
                sys.exit(1)

        if not refresh_token:
            log.error("YOUTUBE_REFRESH_TOKEN not set. Run generate_youtube_token.py first.")
            sys.exit(1)

        _check_token(client_id, client_secret, refresh_token)
        return

    # Full authorization flow
    client_id, client_secret = _load_client_secret(client_secret_path)

    auth_url = _build_auth_url(client_id)

    print("\n" + "=" * 60)
    print("  IRON STATIC — YouTube OAuth Authorization")
    print("=" * 60)
    print("\nOpening your browser to authorize IRON STATIC's YouTube access.")
    print("If the browser does not open, visit this URL manually:\n")
    print(f"  {auth_url}\n")

    webbrowser.open(auth_url)

    auth_code = _run_local_server()
    log.info("Authorization code received.")

    log.info("Exchanging authorization code for tokens ...")
    token_data = _exchange_code(auth_code, client_id, client_secret)

    if "error" in token_data:
        log.error("Token exchange failed: %s", token_data.get("error_description", token_data))
        sys.exit(1)

    refresh_token = token_data.get("refresh_token", "")
    access_token = token_data.get("access_token", "")
    scope = token_data.get("scope", "")

    if not refresh_token:
        log.error(
            "No refresh_token in response. "
            "Make sure access_type=offline and prompt=consent are set. "
            "Also confirm this OAuth Client ID has not been used before — "
            "if it has, Google will not re-issue the refresh token unless you "
            "revoke the app access first: https://myaccount.google.com/permissions"
        )
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  Authorization successful!")
    print("=" * 60)
    print(f"\n  Scopes granted: {scope}")
    print("\n  Add these to your GitHub Actions secrets and local .env:\n")
    print(f"  YOUTUBE_CLIENT_ID={client_id}")
    print(f"  YOUTUBE_CLIENT_SECRET={client_secret}")
    print(f"  YOUTUBE_REFRESH_TOKEN={refresh_token}")
    print("\n  The refresh token does not expire unless revoked.")
    print("  Access tokens are obtained automatically by post_youtube.py.\n")
    print("=" * 60 + "\n")

    _offer_env_write(env_file, client_id, client_secret, refresh_token)


if __name__ == "__main__":
    main()
