#!/usr/bin/env python3
"""
post_tiktok.py — TikTok video upload client for IRON STATIC.

Posts a short video clip to TikTok via the TikTok Content Posting API v2.
Uses a two-step flow: init upload → chunk PUT → poll for status.

TikTok access tokens expire in 24 hours. Refresh tokens are valid for 365 days.
Use refresh_tokens.py (or the refresh-tokens GitHub Actions workflow) to
rotate access tokens automatically.

Auth:
  TikTok for Developers → your app → Content Posting API
  Required scopes: video.publish, video.upload

Environment variables (required):
  TIKTOK_ACCESS_TOKEN     — short-lived access token (refresh via refresh_tokens.py)
  TIKTOK_CLIENT_KEY       — app client_key from TikTok developer portal
  TIKTOK_CLIENT_SECRET    — app client_secret from TikTok developer portal
  TIKTOK_REFRESH_TOKEN    — 365-day refresh token (stored in GitHub Secrets)

Usage:
  python scripts/post_tiktok.py \\
    --content outputs/social/ignition-point_tiktok_caption.txt \\
    --video outputs/social/ignition-point_visualizer_square.mp4

  python scripts/post_tiktok.py \\
    --content outputs/social/ignition-point_tiktok_caption.txt \\
    --video outputs/social/ignition-point_visualizer_square.mp4 \\
    --dry-run
"""

import argparse
import json
import logging
import os
import sys
import time
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

TIKTOK_API_BASE = "https://open.tiktokapis.com"
TOKEN_URL = f"{TIKTOK_API_BASE}/v2/oauth/token/"

# Upload polling: check every 5s for up to 3 minutes
POLL_INTERVAL = 5
POLL_MAX = 36

# TikTok max video size: 4 GB; recommended chunk: 10 MB
CHUNK_SIZE = 10 * 1024 * 1024


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_env(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        log.error("Required environment variable %s is not set.", name)
        sys.exit(1)
    return val


def _refresh_access_token(client_key: str, client_secret: str, refresh_token: str) -> str:
    """Exchange a TikTok refresh token for a new access token."""
    data = urlencode({
        "client_key": client_key,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }).encode()
    req = Request(
        TOKEN_URL,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "no-cache",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read())
            data_block = payload.get("data", payload)
            token = data_block.get("access_token", "")
            if not token:
                log.error("No access_token in TikTok refresh response: %s", payload)
                sys.exit(1)
            expires_in = data_block.get("expires_in", "?")
            log.info("TikTok access token refreshed (expires_in=%s).", expires_in)
            return token
    except HTTPError as exc:
        body = exc.read().decode(errors="replace")
        log.error("Token refresh failed: %s — %s", exc.code, body)
        sys.exit(1)


def _tiktok_post(path: str, access_token: str, data: dict) -> dict:
    body = json.dumps(data).encode()
    req = Request(
        f"{TIKTOK_API_BASE}{path}",
        data=body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except HTTPError as exc:
        body_err = exc.read().decode(errors="replace")
        log.error("TikTok API POST %s error %s: %s", path, exc.code, body_err)
        sys.exit(1)


def _tiktok_get(path: str, access_token: str, params: dict | None = None) -> dict:
    url = f"{TIKTOK_API_BASE}{path}"
    if params:
        url += "?" + urlencode(params)
    req = Request(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except HTTPError as exc:
        body_err = exc.read().decode(errors="replace")
        log.error("TikTok API GET %s error %s: %s", path, exc.code, body_err)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Upload flow
# ---------------------------------------------------------------------------

def _init_upload(access_token: str, video_path: Path, caption: str) -> tuple[str, str, int]:
    """Initialize a video upload. Returns (publish_id, upload_url, chunk_size)."""
    file_size = video_path.stat().st_size
    total_chunks = max(1, (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE)

    payload = {
        "post_info": {
            "title": caption[:2200],  # TikTok caption max 2200 chars
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
            "video_cover_timestamp_ms": 1000,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": file_size,
            "chunk_size": CHUNK_SIZE,
            "total_chunk_count": total_chunks,
        },
    }

    resp = _tiktok_post("/v2/post/publish/video/init/", access_token, payload)
    err = resp.get("error", {})
    if err.get("code", "ok") != "ok":
        log.error("Upload init failed: %s — %s", err.get("code"), err.get("message"))
        sys.exit(1)

    data = resp.get("data", {})
    publish_id = data.get("publish_id", "")
    upload_url = data.get("upload_url", "")
    server_chunk_size = data.get("chunk_size", CHUNK_SIZE)

    if not publish_id or not upload_url:
        log.error("Missing publish_id or upload_url in init response: %s", data)
        sys.exit(1)

    log.info("Upload session initialized. publish_id=%s", publish_id)
    return publish_id, upload_url, server_chunk_size


def _upload_chunks(upload_url: str, video_path: Path, chunk_size: int) -> None:
    """PUT video bytes to TikTok's upload URL in chunks."""
    file_size = video_path.stat().st_size
    total_chunks = max(1, (file_size + chunk_size - 1) // chunk_size)

    with video_path.open("rb") as fh:
        for chunk_idx in range(total_chunks):
            chunk = fh.read(chunk_size)
            chunk_len = len(chunk)
            offset = chunk_idx * chunk_size
            end = offset + chunk_len - 1

            req = Request(
                upload_url,
                data=chunk,
                method="PUT",
                headers={
                    "Content-Range": f"bytes {offset}-{end}/{file_size}",
                    "Content-Length": str(chunk_len),
                    "Content-Type": "video/mp4",
                },
            )
            try:
                with urlopen(req, timeout=120) as resp:
                    log.debug("Chunk %d/%d accepted (status %s).", chunk_idx + 1, total_chunks, resp.status)
            except HTTPError as exc:
                body_err = exc.read().decode(errors="replace")
                log.error("Chunk %d upload error %s: %s", chunk_idx + 1, exc.code, body_err)
                sys.exit(1)

    log.info("All %d chunk(s) uploaded.", total_chunks)


def _poll_publish_status(access_token: str, publish_id: str) -> str:
    """Poll until the video is published or an error occurs. Returns the video ID."""
    for attempt in range(POLL_MAX):
        resp = _tiktok_post(
            "/v2/post/publish/status/fetch/",
            access_token,
            {"publish_id": publish_id},
        )
        err = resp.get("error", {})
        if err.get("code", "ok") != "ok":
            log.error("Status poll error: %s — %s", err.get("code"), err.get("message"))
            sys.exit(1)

        data = resp.get("data", {})
        status = data.get("status", "")
        video_id = data.get("publicaly_available_post_id", [None])
        if isinstance(video_id, list):
            video_id = video_id[0] if video_id else None

        log.info("Publish status: %s (attempt %d/%d)", status, attempt + 1, POLL_MAX)

        if status == "PUBLISH_COMPLETE" and video_id:
            log.info("Video published. video_id=%s", video_id)
            return str(video_id)
        if status in ("FAILED", "REMOVED"):
            log.error("Publish failed with status: %s", status)
            sys.exit(1)

        time.sleep(POLL_INTERVAL)

    log.error("Publish did not complete after %d attempts.", POLL_MAX)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def post_video(
    access_token: str,
    video_path: Path,
    caption: str,
    dry_run: bool,
) -> str | None:
    if dry_run:
        log.info("[DRY RUN] Would post to TikTok:")
        log.info("  Video: %s (%.1f MB)", video_path, video_path.stat().st_size / 1e6)
        log.info("  Caption: %s", caption[:100] + "..." if len(caption) > 100 else caption)
        return None

    publish_id, upload_url, chunk_size = _init_upload(access_token, video_path, caption)
    _upload_chunks(upload_url, video_path, chunk_size)
    video_id = _poll_publish_status(access_token, publish_id)

    tiktok_url = f"https://www.tiktok.com/@ironstaticband/video/{video_id}"
    log.info("TikTok URL: %s", tiktok_url)
    return tiktok_url


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Post a video to TikTok.")
    p.add_argument("--content", type=Path, required=True,
                   help="Text file with caption content")
    p.add_argument("--video", type=Path, required=True,
                   help="MP4 video file to upload")
    p.add_argument("--auto-refresh-token", action="store_true",
                   help="Automatically refresh access token before posting")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    client_key = _require_env("TIKTOK_CLIENT_KEY")
    client_secret = _require_env("TIKTOK_CLIENT_SECRET")
    refresh_token = _require_env("TIKTOK_REFRESH_TOKEN")

    if args.auto_refresh_token or not os.environ.get("TIKTOK_ACCESS_TOKEN"):
        log.info("Refreshing TikTok access token ...")
        access_token = _refresh_access_token(client_key, client_secret, refresh_token)
    else:
        access_token = _require_env("TIKTOK_ACCESS_TOKEN")

    if not args.content.exists():
        log.error("Content file not found: %s", args.content)
        sys.exit(1)
    if not args.video.exists():
        log.error("Video file not found: %s", args.video)
        sys.exit(1)

    caption = args.content.read_text().strip()
    if not caption:
        log.error("Content file is empty: %s", args.content)
        sys.exit(1)

    url = post_video(access_token, args.video, caption, args.dry_run)
    if url:
        log.info("Posted: %s", url)


if __name__ == "__main__":
    main()
