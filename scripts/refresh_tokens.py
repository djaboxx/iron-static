#!/usr/bin/env python3
"""
refresh_tokens.py — Platform OAuth token rotation for IRON STATIC.

Refreshes short-lived access tokens for Instagram and TikTok.
Prints the new token values so they can be manually updated in GitHub Secrets,
or optionally updates them automatically via `gh secret set`.

Platform token lifetimes:
  Instagram  — long-lived token, expires in 60 days. Refresh before day 50.
  TikTok     — access token expires in 24h, refresh token valid 365 days.

Instagram refresh:
  GET https://graph.instagram.com/refresh_access_token
    ?grant_type=ig_refresh_token&access_token=<current_token>
  → returns new access_token + expires_in

TikTok refresh:
  POST https://open.tiktokapis.com/v2/oauth/token/
    grant_type=refresh_token&client_key=...&client_secret=...&refresh_token=...
  → returns access_token + refresh_token + expires_in

The script warns if a token is within 14 days of expiry and exits non-zero
if a token has already expired.

Usage:
  python scripts/refresh_tokens.py --platform all
  python scripts/refresh_tokens.py --platform instagram --dry-run
  python scripts/refresh_tokens.py --platform tiktok --update-secrets
  python scripts/refresh_tokens.py --check-only

Options:
  --platform      instagram | tiktok | all (default: all)
  --check-only    Report expiry status without refreshing
  --update-secrets  Update GitHub Secrets automatically via `gh secret set`
  --dry-run       Print actions without making API calls
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent

_env_file = REPO_ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

WARN_DAYS_BEFORE_EXPIRY = 14

INSTAGRAM_REFRESH_URL = "https://graph.instagram.com/refresh_access_token"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_env(name: str, required: bool = True) -> str:
    val = os.environ.get(name, "")
    if required and not val:
        log.error("Required environment variable %s is not set.", name)
        sys.exit(1)
    return val


def _days_until_expiry(expires_in_seconds: int) -> int:
    return int(expires_in_seconds / 86400)


def _gh_secret_set(secret_name: str, secret_value: str, dry_run: bool) -> None:
    """Update a GitHub repository secret via the `gh` CLI."""
    if dry_run:
        log.info("[DRY RUN] Would run: gh secret set %s", secret_name)
        return
    try:
        result = subprocess.run(  # noqa: S603 — args are from env, not user input
            ["gh", "secret", "set", secret_name, "--body", secret_value],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(REPO_ROOT),
        )
        log.info("Updated GitHub Secret: %s", secret_name)
        if result.stdout:
            log.debug("gh output: %s", result.stdout.strip())
    except subprocess.CalledProcessError as exc:
        log.error("Failed to set secret %s: %s", secret_name, exc.stderr.strip())
    except FileNotFoundError:
        log.error("`gh` CLI not found. Install GitHub CLI to use --update-secrets.")


# ---------------------------------------------------------------------------
# Instagram
# ---------------------------------------------------------------------------

def refresh_instagram(dry_run: bool, update_secrets: bool, check_only: bool) -> bool:
    """
    Refresh the Instagram long-lived access token.
    Returns True if the token is healthy (not expired) after the operation.
    """
    access_token = _get_env("INSTAGRAM_ACCESS_TOKEN", required=False)
    if not access_token:
        log.warning("INSTAGRAM_ACCESS_TOKEN not set — skipping Instagram token refresh.")
        return True

    if check_only:
        # Instagram doesn't expose expiry via a status endpoint without refresh —
        # we can only check by attempting a lightweight API call.
        log.info("Instagram: checking token validity ...")
        check_url = (
            "https://graph.instagram.com/me?fields=id,username"
            f"&access_token={access_token}"
        )
        req = Request(check_url)
        try:
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                log.info("Instagram token is valid. User: %s (id=%s)",
                         data.get("username"), data.get("id"))
                return True
        except HTTPError as exc:
            body = exc.read().decode(errors="replace")
            log.error("Instagram token check failed: %s — %s", exc.code, body)
            return False

    if dry_run:
        log.info("[DRY RUN] Would refresh Instagram access token via graph.instagram.com")
        return True

    params = urlencode({
        "grant_type": "ig_refresh_token",
        "access_token": access_token,
    })
    req = Request(f"{INSTAGRAM_REFRESH_URL}?{params}")
    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except HTTPError as exc:
        body = exc.read().decode(errors="replace")
        log.error("Instagram token refresh failed: %s — %s", exc.code, body)
        return False

    new_token = data.get("access_token", "")
    expires_in = data.get("expires_in", 0)
    days_left = _days_until_expiry(expires_in)

    if not new_token:
        log.error("No access_token in Instagram refresh response: %s", data)
        return False

    log.info("Instagram token refreshed. Expires in %d days.", days_left)
    if days_left < WARN_DAYS_BEFORE_EXPIRY:
        log.warning("Instagram token expires in %d days — plan for re-auth.", days_left)

    print(f"\nINSTAGRAM_ACCESS_TOKEN={new_token}")

    if update_secrets:
        _gh_secret_set("INSTAGRAM_ACCESS_TOKEN", new_token, dry_run=False)

    return days_left > 0


# ---------------------------------------------------------------------------
# TikTok
# ---------------------------------------------------------------------------

def refresh_tiktok(dry_run: bool, update_secrets: bool, check_only: bool) -> bool:
    """
    Refresh the TikTok access + refresh token pair.
    Returns True if the token is healthy after the operation.
    """
    client_key = _get_env("TIKTOK_CLIENT_KEY", required=False)
    client_secret = _get_env("TIKTOK_CLIENT_SECRET", required=False)
    refresh_token = _get_env("TIKTOK_REFRESH_TOKEN", required=False)

    if not all([client_key, client_secret, refresh_token]):
        log.warning("TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET / TIKTOK_REFRESH_TOKEN not fully "
                    "set — skipping TikTok token refresh.")
        return True

    if check_only:
        # TikTok doesn't have a cheap token check endpoint — just report env state
        access_token = os.environ.get("TIKTOK_ACCESS_TOKEN", "")
        if access_token:
            log.info("TikTok: TIKTOK_ACCESS_TOKEN is set (24h lifetime — expected to need refresh).")
        else:
            log.info("TikTok: TIKTOK_ACCESS_TOKEN not set (will be refreshed at post time).")
        log.info("TikTok: refresh token is set (365-day lifetime).")
        return True

    if dry_run:
        log.info("[DRY RUN] Would refresh TikTok access token via %s", TIKTOK_TOKEN_URL)
        return True

    data = urlencode({
        "client_key": client_key,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }).encode()
    req = Request(
        TIKTOK_TOKEN_URL,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "no-cache",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read())
    except HTTPError as exc:
        body = exc.read().decode(errors="replace")
        log.error("TikTok token refresh failed: %s — %s", exc.code, body)
        return False

    data_block = payload.get("data", payload)
    new_access_token = data_block.get("access_token", "")
    new_refresh_token = data_block.get("refresh_token", refresh_token)
    access_expires_in = data_block.get("expires_in", 86400)
    refresh_expires_in = data_block.get("refresh_expires_in", 365 * 86400)

    if not new_access_token:
        log.error("No access_token in TikTok refresh response: %s", payload)
        return False

    access_days = _days_until_expiry(access_expires_in)
    refresh_days = _days_until_expiry(refresh_expires_in)
    log.info("TikTok access token refreshed (expires_in=%ds = ~%dh).", access_expires_in, access_expires_in // 3600)
    log.info("TikTok refresh token valid for %d more days.", refresh_days)

    if refresh_days < WARN_DAYS_BEFORE_EXPIRY:
        log.warning("TikTok refresh token expires in %d days — re-auth required soon!", refresh_days)

    print(f"\nTIKTOK_ACCESS_TOKEN={new_access_token}")
    if new_refresh_token != refresh_token:
        print(f"TIKTOK_REFRESH_TOKEN={new_refresh_token}")

    if update_secrets:
        _gh_secret_set("TIKTOK_ACCESS_TOKEN", new_access_token, dry_run=False)
        if new_refresh_token != refresh_token:
            _gh_secret_set("TIKTOK_REFRESH_TOKEN", new_refresh_token, dry_run=False)

    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Refresh platform OAuth tokens for IRON STATIC.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--platform",
        choices=["instagram", "tiktok", "all"],
        default="all",
        help="Which platform to refresh (default: all)",
    )
    p.add_argument(
        "--check-only",
        action="store_true",
        help="Check token validity without refreshing",
    )
    p.add_argument(
        "--update-secrets",
        action="store_true",
        help="Auto-update GitHub Secrets via `gh secret set` after refresh",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without making API calls",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    success = True
    platform = args.platform

    if platform in ("instagram", "all"):
        ok = refresh_instagram(
            dry_run=args.dry_run,
            update_secrets=args.update_secrets,
            check_only=args.check_only,
        )
        success = success and ok

    if platform in ("tiktok", "all"):
        ok = refresh_tiktok(
            dry_run=args.dry_run,
            update_secrets=args.update_secrets,
            check_only=args.check_only,
        )
        success = success and ok

    if not success:
        log.error("One or more token operations failed.")
        sys.exit(1)

    if not args.check_only and not args.dry_run and not args.update_secrets:
        log.info("\nNew token values printed above. Update GitHub Secrets manually, or re-run with --update-secrets.")


if __name__ == "__main__":
    main()
