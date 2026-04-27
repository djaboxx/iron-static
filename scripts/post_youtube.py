#!/usr/bin/env python3
"""
post_youtube.py — YouTube Data API v3 upload client for IRON STATIC.

Uploads a video (MP4 or other supported format) to the IRON STATIC YouTube channel
using OAuth 2.0 with a refresh token — no browser interaction required in CI.

Default privacy is 'unlisted'. Dave reviews and makes it public manually.
Never set --privacy public by default in automated workflows.

Auth flow:
  1. YOUTUBE_CLIENT_ID + YOUTUBE_CLIENT_SECRET + YOUTUBE_REFRESH_TOKEN are read
     from environment (or .env). Generate them once with generate_youtube_token.py.
  2. A short-lived access token is obtained from the refresh token on each run.
  3. The video is uploaded using a resumable upload session (required for large files).

YouTube Data API v3 quota: 10,000 units/day free. Video upload = 1600 units.
Budget: ~6 uploads/day on free tier.

Usage:
  python scripts/post_youtube.py --video outputs/social/ignition-point_visualizer_landscape.mp4
  python scripts/post_youtube.py --song ignition-point   # auto-resolve video, title, description
  python scripts/post_youtube.py --video ... --title "..." --description outputs/social/cap.txt
  python scripts/post_youtube.py --video ... --privacy public   # ONLY after Dave reviews
  python scripts/post_youtube.py --dry-run   # print all params without uploading
  python scripts/post_youtube.py --check-token   # verify auth works

Required environment variables:
  YOUTUBE_CLIENT_ID       — from Google Cloud Console (OAuth 2.0 Desktop app)
  YOUTUBE_CLIENT_SECRET   — from Google Cloud Console
  YOUTUBE_REFRESH_TOKEN   — generated once by scripts/generate_youtube_token.py

Optional:
  YOUTUBE_CHANNEL_ID      — if you want to verify the upload landed on the right channel
"""

import argparse
import json
import logging
import math
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

REPO_ROOT = Path(__file__).resolve().parent.parent
SONGS_PATH = REPO_ROOT / "database" / "songs.json"
SOCIAL_OUT = REPO_ROOT / "outputs" / "social"

OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_UPLOAD_BASE = "https://www.googleapis.com/upload/youtube/v3"

# Resumable upload chunk size: 8MB (must be multiple of 256KB)
CHUNK_SIZE = 8 * 1024 * 1024

# Retry config for resumable upload
MAX_RETRIES = 5
RETRY_BACKOFF_BASE = 2  # seconds

VALID_PRIVACY = {"private", "unlisted", "public"}

# ---------------------------------------------------------------------------
# Env / .env loading
# ---------------------------------------------------------------------------

_env_file = REPO_ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())


def _get_env(name: str, required: bool = True) -> str:
    val = os.environ.get(name, "")
    if not val and required:
        log.error("Environment variable %s is not set.", name)
        log.error(
            "Run scripts/generate_youtube_token.py once to set up credentials, "
            "then add them to .env or GitHub Actions secrets."
        )
        sys.exit(1)
    return val


# ---------------------------------------------------------------------------
# OAuth: refresh token → access token
# ---------------------------------------------------------------------------

def _get_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    """Exchange refresh token for a short-lived access token."""
    log.info("Obtaining access token from refresh token ...")
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
    except HTTPError as exc:
        body_text = exc.read().decode(errors="replace")
        log.error("Token refresh HTTP %d: %s", exc.code, body_text)
        sys.exit(1)

    if "error" in data:
        log.error(
            "Token refresh error: %s — %s",
            data.get("error"), data.get("error_description", "")
        )
        log.error("Run scripts/generate_youtube_token.py to re-authorize.")
        sys.exit(1)

    access_token = data.get("access_token", "")
    expires_in = data.get("expires_in", 0)
    log.info("Access token obtained (expires in %ds).", expires_in)
    return access_token


def check_token(client_id: str, client_secret: str, refresh_token: str) -> None:
    """Verify token works and print channel info."""
    access_token = _get_access_token(client_id, client_secret, refresh_token)

    url = f"{YOUTUBE_API_BASE}/channels?part=snippet&mine=true"
    req = Request(url, headers={
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    })
    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except HTTPError as exc:
        log.error("Channel check HTTP %d: %s", exc.code, exc.read().decode(errors="replace"))
        sys.exit(1)

    items = data.get("items", [])
    if not items:
        log.warning("No YouTube channel found for this account.")
        return

    channel = items[0]["snippet"]
    log.info("Token valid. Channel: %s (id: %s)", channel.get("title"), items[0].get("id"))


# ---------------------------------------------------------------------------
# Resumable upload
# ---------------------------------------------------------------------------

def _initiate_resumable_upload(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    privacy: str,
    access_token: str,
) -> str:
    """Initiate a resumable upload session and return the upload URI."""
    metadata = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "10",  # 10 = Music
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    body = json.dumps(metadata).encode()
    file_size = video_path.stat().st_size

    url = (
        f"{YOUTUBE_UPLOAD_BASE}/videos"
        f"?uploadType=resumable&part=snippet,status"
    )
    req = Request(url, data=body, headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/*",
        "X-Upload-Content-Length": str(file_size),
    })

    try:
        with urlopen(req, timeout=30) as resp:
            upload_uri = resp.headers.get("Location", "")
    except HTTPError as exc:
        log.error(
            "Failed to initiate upload HTTP %d: %s",
            exc.code, exc.read().decode(errors="replace")
        )
        sys.exit(1)

    if not upload_uri:
        log.error("No upload URI returned from initiation request.")
        sys.exit(1)

    log.info("Resumable upload session initiated.")
    return upload_uri


def _upload_video_chunks(video_path: Path, upload_uri: str) -> dict:
    """Upload video in chunks. Returns the completed video resource."""
    file_size = video_path.stat().st_size
    total_chunks = math.ceil(file_size / CHUNK_SIZE)
    log.info(
        "Uploading %s (%.1f MB) in %d chunks ...",
        video_path.name, file_size / 1024 / 1024, total_chunks
    )

    with open(video_path, "rb") as f:
        chunk_index = 0
        offset = 0

        while offset < file_size:
            chunk = f.read(CHUNK_SIZE)
            chunk_end = offset + len(chunk) - 1

            for attempt in range(MAX_RETRIES):
                req = Request(upload_uri, data=chunk, headers={
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {offset}-{chunk_end}/{file_size}",
                })
                req.get_method = lambda: "PUT"

                try:
                    with urlopen(req, timeout=120) as resp:
                        status = resp.status
                        if status in (200, 201):
                            # Upload complete
                            return json.loads(resp.read())
                        # 308 Resume Incomplete — continue
                        break
                except HTTPError as exc:
                    if exc.code == 308:
                        # Resume Incomplete — this is expected mid-upload
                        break
                    if exc.code in (500, 502, 503, 504) and attempt < MAX_RETRIES - 1:
                        wait = RETRY_BACKOFF_BASE ** attempt
                        log.warning(
                            "Chunk %d/%d HTTP %d — retrying in %ds ...",
                            chunk_index + 1, total_chunks, exc.code, wait
                        )
                        time.sleep(wait)
                        continue
                    log.error(
                        "Chunk %d/%d upload failed HTTP %d: %s",
                        chunk_index + 1, total_chunks, exc.code,
                        exc.read().decode(errors="replace")
                    )
                    sys.exit(1)

            pct = int((offset + len(chunk)) / file_size * 100)
            log.info("  Chunk %d/%d — %d%%", chunk_index + 1, total_chunks, pct)
            offset += len(chunk)
            chunk_index += 1

    log.error("Upload loop exited without completion.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Song / file resolution
# ---------------------------------------------------------------------------

def _load_song(slug: str | None) -> dict | None:
    if not SONGS_PATH.exists():
        return None
    with open(SONGS_PATH) as f:
        db = json.load(f)
    songs = db.get("songs", [])
    if slug:
        matches = [s for s in songs if s["slug"] == slug]
        return matches[0] if matches else None
    active = [s for s in songs if s.get("status") == "active"]
    return active[0] if active else None


def _resolve_video(args, song: dict | None) -> Path:
    if args.video:
        p = Path(args.video)
        if not p.is_absolute():
            p = REPO_ROOT / p
        if not p.exists():
            log.error("Video file not found: %s", p)
            sys.exit(1)
        return p

    if song:
        slug = song["slug"]
        # Prefer landscape for YouTube
        for suffix in ("_visualizer_landscape.mp4", "_visualizer_landscape.mov",
                       "_landscape.mp4", ".mp4"):
            candidate = SOCIAL_OUT / f"{slug}{suffix}"
            if candidate.exists():
                log.info("Auto-resolved video: %s", candidate)
                return candidate

        log.error("No video found for song '%s' in %s", slug, SOCIAL_OUT)
        log.error(
            "Run The Video Director to render a visualizer, then retry. "
            "Expected: %s/%s_visualizer_landscape.mp4", SOCIAL_OUT, slug
        )
        sys.exit(1)

    log.error("No --video specified and no active song.")
    sys.exit(1)


def _resolve_title(args, song: dict | None, video_path: Path) -> str:
    if args.title:
        return args.title
    if song:
        return f"{song.get('title', song['slug'])} — IRON STATIC"
    return video_path.stem.replace("_", " ").title()


def _resolve_description(args, song: dict | None) -> str:
    if args.description:
        p = Path(args.description)
        if not p.is_absolute():
            p = REPO_ROOT / p
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
        # Treat as literal description string
        return args.description

    if song:
        slug = song["slug"]
        candidate = SOCIAL_OUT / f"{slug}_caption_youtube.txt"
        if candidate.exists():
            log.info("Auto-resolved description: %s", candidate)
            return candidate.read_text(encoding="utf-8").strip()
        log.warning(
            "No YouTube caption file found. Generating one now ..."
        )
        import subprocess
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "generate_caption.py"),
             "--song", slug, "--platform", "youtube"],
            capture_output=True, text=True, cwd=str(REPO_ROOT)
        )
        if result.returncode == 0 and candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()
        log.warning("Caption generation failed. Uploading with minimal description.")

    return "IRON STATIC. Heavy. Weird. Electronic. Intentional."


def _resolve_tags(args, song: dict | None) -> list[str]:
    base_tags = ["iron static", "electronic metal", "industrial metal", "heavy electronic"]
    if args.tags:
        extra = [t.strip() for t in args.tags.split(",") if t.strip()]
        return base_tags + extra
    if song:
        slug = song["slug"]
        title_words = song.get("title", "").lower().split()
        return base_tags + [slug] + title_words[:3]
    return base_tags


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload a video to IRON STATIC's YouTube channel."
    )
    parser.add_argument(
        "--video",
        help="Path to the video file (MP4 recommended). Auto-resolved from --song if omitted.",
    )
    parser.add_argument(
        "--song",
        help="Song slug — auto-resolves video, title, and description.",
    )
    parser.add_argument(
        "--title",
        help="Video title. Defaults to '[Song Title] — IRON STATIC'.",
    )
    parser.add_argument(
        "--description",
        help="Description text or path to a .txt file. Auto-resolved from outputs/social/ if omitted.",
    )
    parser.add_argument(
        "--tags",
        help="Comma-separated tags to add (base tags always included).",
    )
    parser.add_argument(
        "--privacy",
        choices=list(VALID_PRIVACY),
        default="unlisted",
        help="Privacy status (default: unlisted). Always use unlisted — Dave publishes manually.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print all parameters without uploading.",
    )
    parser.add_argument(
        "--check-token",
        action="store_true",
        help="Verify auth works and print channel info, then exit.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Debug logging.")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    client_id = _get_env("YOUTUBE_CLIENT_ID")
    client_secret = _get_env("YOUTUBE_CLIENT_SECRET")
    refresh_token = _get_env("YOUTUBE_REFRESH_TOKEN")

    if args.check_token:
        check_token(client_id, client_secret, refresh_token)
        return

    song = _load_song(args.song)
    if song is None and args.song:
        log.error("Song '%s' not found in database/songs.json.", args.song)
        sys.exit(1)

    video_path = _resolve_video(args, song)
    title = _resolve_title(args, song, video_path)
    description = _resolve_description(args, song)
    tags = _resolve_tags(args, song)
    privacy = args.privacy

    if privacy == "public":
        log.warning(
            "Uploading as PUBLIC. This is visible immediately. "
            "Recommended: use --privacy unlisted and publish manually."
        )

    log.info("Song:        %s", song["title"] if song else "(none)")
    log.info("Video:       %s (%.1f MB)", video_path, video_path.stat().st_size / 1024 / 1024)
    log.info("Title:       %s", title)
    log.info("Privacy:     %s", privacy)
    log.info("Tags:        %s", ", ".join(tags))
    log.info("Description: %.120s ...", description)

    if args.dry_run:
        log.info("[DRY RUN] Would initiate resumable upload to YouTube Data API v3.")
        log.info("[DRY RUN] No API calls made.")
        return

    access_token = _get_access_token(client_id, client_secret, refresh_token)

    upload_uri = _initiate_resumable_upload(
        video_path, title, description, tags, privacy, access_token
    )

    video_resource = _upload_video_chunks(video_path, upload_uri)

    video_id = video_resource.get("id", "")
    video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else "(unknown)"
    privacy_status = (
        video_resource.get("status", {}).get("privacyStatus", privacy)
    )

    log.info("Upload complete.")
    log.info("Video ID:    %s", video_id)
    log.info("URL:         %s", video_url)
    log.info("Privacy:     %s", privacy_status)

    if privacy_status == "unlisted":
        log.info("The video is unlisted. Share the URL with Dave to review, then publish manually.")

    # Write the video URL to outputs/social/ for downstream use
    if song:
        url_out = SOCIAL_OUT / f"{song['slug']}_youtube_url.txt"
        SOCIAL_OUT.mkdir(parents=True, exist_ok=True)
        url_out.write_text(video_url + "\n", encoding="utf-8")
        log.info("Video URL saved to: %s", url_out)

    print(f"\nYouTube upload complete: {video_url}\n")


if __name__ == "__main__":
    main()
