#!/usr/bin/env python3
"""
notify_slack.py — Post a notification to a Slack incoming webhook.

Used by GitHub Actions workflows to report pass/fail, token warnings,
and other pipeline events into a Slack channel.

Usage:
    python scripts/notify_slack.py \
        --title "Publish Release" \
        --status success \
        --text "ignition-point published to SoundCloud + YouTube" \
        --workflow "publish-release.yml" \
        --run-url "https://github.com/djaboxx/iron-static/actions/runs/123"

Environment:
    SLACK_WEBHOOK_URL   Incoming webhook URL from api.slack.com/apps

Exit codes:
    0  Posted (or dry-run)
    1  Missing SLACK_WEBHOOK_URL or HTTP error
"""

import argparse
import json
import logging
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
_env_file = REPO_ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Status → color + icon
# ---------------------------------------------------------------------------

STATUS_META: dict[str, dict] = {
    "success": {"color": "#2eb67d", "icon": "✅"},
    "failure": {"color": "#e01e5a", "icon": "❌"},
    "warning": {"color": "#ecb22e", "icon": "⚠️"},
    "info":    {"color": "#36c5f0", "icon": "ℹ️"},
}


def _status_meta(status: str) -> dict:
    return STATUS_META.get(status.lower(), STATUS_META["info"])


# ---------------------------------------------------------------------------
# Block Kit payload builder
# ---------------------------------------------------------------------------

def build_payload(
    title: str,
    text: str,
    status: str,
    workflow: str | None,
    run_url: str | None,
    song_slug: str | None,
) -> dict:
    meta = _status_meta(status)
    icon = meta["icon"]
    color = meta["color"]

    header_text = f"{icon} *{title}*"
    if song_slug:
        header_text += f"  ·  `{song_slug}`"

    body_lines = [text] if text else []
    if workflow:
        body_lines.append(f"Workflow: `{workflow}`")
    if run_url:
        body_lines.append(f"<{run_url}|View run →>")

    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": header_text},
        },
    ]
    if body_lines:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "\n".join(body_lines)},
        })
    blocks.append({"type": "divider"})

    return {
        "attachments": [
            {
                "color": color,
                "blocks": blocks,
            }
        ]
    }


# ---------------------------------------------------------------------------
# HTTP post
# ---------------------------------------------------------------------------

def post_to_slack(webhook_url: str, payload: dict, dry_run: bool = False) -> None:
    body = json.dumps(payload).encode("utf-8")
    if dry_run:
        log.info("[dry-run] Would POST to Slack:\n%s", json.dumps(payload, indent=2))
        return

    req = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            response_text = resp.read().decode("utf-8")
            if resp.status != 200:
                log.error("Slack returned HTTP %d: %s", resp.status, response_text)
                sys.exit(1)
            log.info("Slack notified (HTTP 200)")
    except urllib.error.HTTPError as exc:
        log.error("Slack HTTP error %d: %s", exc.code, exc.read().decode("utf-8", errors="replace"))
        sys.exit(1)
    except urllib.error.URLError as exc:
        log.error("Slack request failed: %s", exc.reason)
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Post a Slack notification for IRON STATIC pipelines.")
    p.add_argument("--title",       required=True, help="Short notification title")
    p.add_argument("--text",        default="",    help="Body text (markdown supported)")
    p.add_argument("--status",      default="info",
                   choices=["success", "failure", "warning", "info"],
                   help="Message status (controls color and icon)")
    p.add_argument("--workflow",    default=None,  help="Workflow filename (e.g. publish-release.yml)")
    p.add_argument("--run-url",     default=None,  help="GitHub Actions run URL")
    p.add_argument("--song-slug",   default=None,  help="Active song slug for context")
    p.add_argument("--webhook-url", default=None,
                   help="Slack webhook URL (falls back to SLACK_WEBHOOK_URL env var)")
    p.add_argument("--dry-run",     action="store_true",
                   help="Print payload without posting")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    webhook_url = args.webhook_url or os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url and not args.dry_run:
        log.error(
            "No Slack webhook URL. Set SLACK_WEBHOOK_URL env var or pass --webhook-url. "
            "See database/homework.json item 'slack-webhook' for setup instructions."
        )
        sys.exit(1)

    # Try to get song slug from database if not provided
    song_slug = args.song_slug
    if not song_slug:
        songs_path = REPO_ROOT / "database" / "songs.json"
        if songs_path.exists():
            try:
                songs_data = json.loads(songs_path.read_text())
                for s in songs_data.get("songs", []):
                    if s.get("status") == "active":
                        song_slug = s.get("slug")
                        break
            except Exception:
                pass  # non-fatal

    payload = build_payload(
        title=args.title,
        text=args.text,
        status=args.status,
        workflow=args.workflow,
        run_url=args.run_url,
        song_slug=song_slug,
    )

    post_to_slack(webhook_url, payload, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
