#!/usr/bin/env python3
"""
post_patreon.py — Patreon post client for IRON STATIC.

Creates a post on the IRON STATIC Patreon campaign via the Patreon API v2.
Supports tier-gating (public, patron, static, in-the-machine) and optional
image attachments.

Tier → minimum pledge mapping (in cents):
  public          — 0     (visible to everyone, not logged in)
  patron          — 0     (visible to all patrons regardless of tier)
  static          — 800   ($8/month Static tier)
  in-the-machine  — 2000  ($20/month In The Machine tier)

Authentication:
  Creator Access Token (Patreon Developers → My Clients → your app → Creator's Access Token).
  This is a long-lived token scoped to your campaign. Rotate as needed.

Environment variables (required):
  PATREON_ACCESS_TOKEN    — creator access token from Patreon developer portal
  PATREON_CAMPAIGN_ID     — numeric campaign ID (find via GET /api/oauth2/v2/campaigns)

Usage:
  # Song release — read copy from .md file
  python scripts/post_patreon.py \\
    --song-slug ignition-point \\
    --copy outputs/social/ignition-point_release_copy.md \\
    --tier public

  # Standalone content post from a file
  python scripts/post_patreon.py \\
    --content outputs/social/ignition-point_patreon_post.md \\
    --tier static \\
    --attachment outputs/social/ignition-point_cover.jpg

  # Dry run (print what would be posted)
  python scripts/post_patreon.py --song-slug ignition-point \\
    --copy outputs/social/ignition-point_release_copy.md \\
    --tier public --dry-run
"""

import argparse
import json
import logging
import os
import sys
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

SONGS_PATH = REPO_ROOT / "database" / "songs.json"
SOCIAL_OUT = REPO_ROOT / "outputs" / "social"

PATREON_API_BASE = "https://www.patreon.com/api/oauth2/v2"

TIER_CENTS = {
    "public": 0,
    "patron": 0,
    "static": 800,
    "in-the-machine": 2000,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_env(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        log.error("Required environment variable %s is not set.", name)
        sys.exit(1)
    return val


def _load_songs() -> list:
    if not SONGS_PATH.exists():
        return []
    db = json.loads(SONGS_PATH.read_text())
    return db.get("songs", db) if isinstance(db, dict) else db


def _get_song(slug: str) -> dict:
    songs = _load_songs()
    match = next((s for s in songs if s["slug"] == slug), None)
    if not match:
        log.error("Song slug '%s' not found in songs.json.", slug)
        sys.exit(1)
    return match


def _extract_content(copy_path: Path) -> tuple[str, str]:
    """Return (title, body) from a release copy / content markdown file.

    Looks for:
      - First H1 (# Title) → post title
      - '## Patreon' section → post body
      - Fallback: full file text → body, filename stem → title
    """
    text = copy_path.read_text().strip()
    title = ""
    body = text

    # Extract H1 as title
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("##"):
            title = stripped.lstrip("# ").strip()
            break

    # Extract Patreon-specific section
    for marker in ["## Patreon", "## patreon"]:
        if marker in text:
            after = text.split(marker, 1)[1]
            block = after.split("\n##")[0].strip()
            if block:
                body = block
                break

    if not title:
        title = copy_path.stem.replace("-", " ").replace("_", " ").title()

    return title, body


def _patreon_request(method: str, path: str, access_token: str, data: dict | None = None) -> dict:
    body = json.dumps(data).encode() if data else b""
    req = Request(
        f"{PATREON_API_BASE}{path}",
        data=body if method in ("POST", "PATCH") else None,
        method=method,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except HTTPError as exc:
        body_err = exc.read().decode(errors="replace")
        log.error("Patreon API %s %s error %s: %s", method, path, exc.code, body_err)
        sys.exit(1)


def _upload_attachment(access_token: str, post_id: str, image_path: Path) -> None:
    """
    Attach an image to a Patreon post.

    Patreon v2 attachment flow:
      1. POST /media with Content-Type image/* → get upload_url + media_id
      2. PUT upload_url with raw image bytes
      3. PATCH /posts/{post_id}/relationships/attachments with media_id
    """
    image_bytes = image_path.read_bytes()
    ctype = "image/jpeg" if image_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"

    # Step 1: request media upload slot
    media_payload = {
        "data": {
            "type": "media",
            "attributes": {
                "owner_type": "post",
                "owner_id": post_id,
                "file_name": image_path.name,
                "media_type": ctype,
            },
        }
    }
    media_resp = _patreon_request("POST", "/media", access_token, media_payload)
    upload_url = media_resp.get("data", {}).get("attributes", {}).get("upload_url", "")
    if not upload_url:
        log.warning("No upload_url in media response — skipping attachment.")
        return

    # Step 2: PUT image bytes to the presigned URL
    put_req = Request(
        upload_url,
        data=image_bytes,
        method="PUT",
        headers={"Content-Type": ctype, "Content-Length": str(len(image_bytes))},
    )
    try:
        with urlopen(put_req, timeout=60):
            log.info("Attachment uploaded: %s", image_path.name)
    except HTTPError as exc:
        body_err = exc.read().decode(errors="replace")
        log.warning("Attachment PUT failed: %s — %s (non-fatal)", exc.code, body_err)


# ---------------------------------------------------------------------------
# Main post
# ---------------------------------------------------------------------------

def post(
    campaign_id: str,
    title: str,
    body: str,
    tier: str,
    access_token: str,
    attachment: Path | None,
    dry_run: bool,
) -> str | None:
    """Create a Patreon post. Returns the post URL on success."""
    min_cents = TIER_CENTS.get(tier, 0)

    # is_public controls whether non-patrons can see the post at all
    is_public = tier == "public"

    if dry_run:
        log.info("[DRY RUN] Would post to Patreon campaign %s:", campaign_id)
        log.info("  Title: %s", title)
        log.info("  Tier: %s (min_cents=%d, is_public=%s)", tier, min_cents, is_public)
        log.info("  Body: %d chars", len(body))
        if attachment:
            log.info("  Attachment: %s", attachment)
        return None

    payload = {
        "data": {
            "type": "post",
            "attributes": {
                "title": title,
                "content": body,
                "is_paid": False,
                "is_public": is_public,
                "min_cents_pledged_to_view": min_cents,
                "post_type": "text_only" if not attachment else "image_file",
            },
            "relationships": {
                "campaign": {
                    "data": {"type": "campaign", "id": campaign_id}
                }
            },
        }
    }

    log.info("Creating Patreon post: '%s' (tier=%s) ...", title, tier)
    resp = _patreon_request("POST", "/posts", access_token, payload)

    post_id = resp.get("data", {}).get("id", "")
    post_url = resp.get("data", {}).get("attributes", {}).get("url", "")
    log.info("Post created: id=%s url=%s", post_id, post_url)

    if attachment and attachment.exists() and post_id:
        log.info("Uploading attachment ...")
        _upload_attachment(access_token, post_id, attachment)

    return post_url


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create a Patreon post.")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--song-slug", help="Song slug from songs.json (auto-builds title/body)")
    src.add_argument("--content", type=Path, help="Markdown file with post content")
    p.add_argument("--copy", type=Path, help="Release copy .md file (used with --song-slug)")
    p.add_argument("--tier", choices=list(TIER_CENTS.keys()), default="public",
                   help="Tier gating (default: public)")
    p.add_argument("--attachment", type=Path, help="Optional image to attach to the post")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    access_token = _require_env("PATREON_ACCESS_TOKEN")
    campaign_id = _require_env("PATREON_CAMPAIGN_ID")

    if args.song_slug:
        song = _get_song(args.song_slug)
        if args.copy and args.copy.exists():
            title, body = _extract_content(args.copy)
            if not title:
                title = f"IRON STATIC — {song.get('title', args.song_slug)}"
        else:
            title = f"IRON STATIC — {song.get('title', args.song_slug)}"
            key = song.get("key", "")
            scale = song.get("scale", "")
            bpm = song.get("bpm", "")
            key_info = f"{key} {scale}, {bpm} BPM".strip(", ") if key else ""
            body = (
                f"**{title}** is out now.\n\n"
                f"{'(' + key_info + ')' + chr(10) + chr(10) if key_info else ''}"
                "Produced by Dave Arnold\n"
                "Brainstorm + Sonic Spec: Gemini\n"
                "Session Partner: GitHub Copilot (Arc)\n"
                "Vocals: VELA (ElevenLabs)\n\n"
                "Stream on [SoundCloud](https://soundcloud.com/ironstaticband) and "
                "[YouTube](https://youtube.com/@ironstaticband).\n\n"
                "Thank you for being part of the machine."
            )
    elif args.content and args.content.exists():
        title, body = _extract_content(args.content)
    else:
        log.error("Provide --song-slug or --content.")
        sys.exit(1)

    post_url = post(
        campaign_id=campaign_id,
        title=title,
        body=body,
        tier=args.tier,
        access_token=access_token,
        attachment=args.attachment,
        dry_run=args.dry_run,
    )
    if post_url:
        log.info("Patreon post URL: %s", post_url)


if __name__ == "__main__":
    main()
