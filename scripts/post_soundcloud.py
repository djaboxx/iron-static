#!/usr/bin/env python3
"""
post_soundcloud.py — SoundCloud upload client for IRON STATIC.

Uploads a WAV or MP3 master to SoundCloud via the SoundCloud API v2.
Audio is pulled from GCS (by GCS path) or from a local file.
Cover art is pulled from GCS or from a local JPEG/PNG file.
Release copy (description) is read from a release copy Markdown file.

API flow:
  1. POST /tracks (multipart) — upload audio + artwork + metadata
  2. PATCH /tracks/{id} — set sharing to "public" once upload is confirmed

Auth:
  SoundCloud OAuth2 client credentials flow (app-level token, no user interaction):
    POST /oauth2/token with grant_type=client_credentials

Environment variables (required):
  SOUNDCLOUD_CLIENT_ID       — from soundcloud.com/you/apps
  SOUNDCLOUD_CLIENT_SECRET   — from soundcloud.com/you/apps

Environment variables (optional):
  GCS_BUCKET    — to pull audio/art from GCS
  GCS_SA_KEY    — service account JSON for GCS

Usage:
  python scripts/post_soundcloud.py --song-slug ignition-point \\
    --audio audio/generated/ignition-point_master_v1.wav \\
    --artwork outputs/social/ignition-point_cover_square.jpg \\
    --copy outputs/social/ignition-point_release_copy.md

  python scripts/post_soundcloud.py --song-slug ignition-point \\
    --gcs-audio audio/generated/ignition-point_master_v1.wav \\
    --gcs-artwork audio/generated/ignition-point_cover_3000.jpg \\
    --copy outputs/social/ignition-point_release_copy.md

  python scripts/post_soundcloud.py --song-slug ignition-point ... --dry-run
"""

import argparse
import json
import logging
import os
import sys
import tempfile
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

SC_API_BASE = "https://api.soundcloud.com"
SONGS_PATH = REPO_ROOT / "database" / "songs.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_env(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        log.error("Required environment variable %s is not set.", name)
        sys.exit(1)
    return val


def _get_access_token(client_id: str, client_secret: str) -> str:
    """Exchange client credentials for an OAuth2 access token."""
    data = urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }).encode()
    req = Request(
        f"{SC_API_BASE}/oauth2/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )
    try:
        with urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read())
            token = payload.get("access_token", "")
            if not token:
                log.error("No access_token in response: %s", payload)
                sys.exit(1)
            log.info("Obtained SoundCloud access token (expires_in=%s).", payload.get("expires_in"))
            return token
    except HTTPError as exc:
        body = exc.read().decode(errors="replace")
        log.error("Token request failed: %s — %s", exc.code, body)
        sys.exit(1)


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


def _extract_description(copy_path: Path) -> str:
    """Extract the description block from a release copy markdown file.

    Looks for a '## SoundCloud' or '## Description' section first,
    then falls back to the full file content stripped of markdown headers.
    """
    text = copy_path.read_text()
    # Look for a SoundCloud-specific section
    for marker in ["## SoundCloud", "## Description", "## soundcloud"]:
        if marker in text:
            after = text.split(marker, 1)[1]
            # Take content up to next ## heading
            block = after.split("\n##")[0].strip()
            if block:
                return block
    # Fallback: strip markdown headers and return cleaned text
    lines = [l for l in text.splitlines() if not l.startswith("#")]
    return "\n".join(lines).strip()


def _pull_from_gcs(gcs_path: str, local_dest: Path) -> None:
    """Download a GCS object to a local path. Requires google-cloud-storage."""
    try:
        from google.cloud import storage  # type: ignore
        from google.oauth2.service_account import Credentials  # type: ignore
    except ImportError:
        log.error("google-cloud-storage is required for GCS pulls. pip install google-cloud-storage")
        sys.exit(1)

    bucket_name = _require_env("GCS_BUCKET")
    sa_key_json = os.environ.get("GCS_SA_KEY", "")
    if sa_key_json:
        import json as _json
        creds = Credentials.from_service_account_info(_json.loads(sa_key_json))
        client = storage.Client(credentials=creds)
    else:
        client = storage.Client()

    blob = client.bucket(bucket_name).blob(gcs_path.lstrip("/"))
    local_dest.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(local_dest))
    log.info("Downloaded gs://%s/%s → %s", bucket_name, gcs_path, local_dest)


# ---------------------------------------------------------------------------
# Multipart POST helper (stdlib only — no requests dependency)
# ---------------------------------------------------------------------------

def _multipart_post(url: str, token: str, fields: dict, files: dict) -> dict:
    """
    fields: {name: str_value}
    files:  {name: (filename, bytes, content_type)}
    """
    boundary = "IronStaticBoundary" + str(int(time.time()))
    parts = []

    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f'{value}\r\n'
        )

    file_parts = []
    for name, (filename, data, ctype) in files.items():
        header = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            f'Content-Type: {ctype}\r\n\r\n'
        ).encode()
        file_parts.append(header + data + b'\r\n')

    body = "".join(parts).encode() + b"".join(file_parts) + f"--{boundary}--\r\n".encode()

    req = Request(
        url,
        data=body,
        headers={
            "Authorization": f"OAuth {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except HTTPError as exc:
        body_err = exc.read().decode(errors="replace")
        log.error("SoundCloud API error %s: %s", exc.code, body_err)
        sys.exit(1)


def _sc_patch(url: str, token: str, data: dict) -> dict:
    body = urlencode(data).encode()
    req = Request(
        url,
        data=body,
        method="PUT",
        headers={
            "Authorization": f"OAuth {token}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except HTTPError as exc:
        body_err = exc.read().decode(errors="replace")
        log.error("SoundCloud PATCH error %s: %s", exc.code, body_err)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main upload
# ---------------------------------------------------------------------------

def upload(
    song: dict,
    audio_path: Path,
    artwork_path: Path | None,
    description: str,
    token: str,
    dry_run: bool,
) -> str | None:
    """Upload track to SoundCloud. Returns the track URL on success."""
    title = song.get("title", song["slug"])
    key = song.get("key", "")
    bpm = song.get("bpm", "")
    tags = "ironstaticband industrial electronic metal experimental ai music machine music"
    if bpm:
        tags += f" {bpm}bpm"

    if dry_run:
        log.info("[DRY RUN] Would upload: %s", title)
        log.info("  Audio: %s", audio_path)
        log.info("  Artwork: %s", artwork_path)
        log.info("  Description: %s chars", len(description))
        return None

    fields = {
        "track[title]": title,
        "track[description]": description,
        "track[genre]": "Industrial Electronic",
        "track[tag_list]": tags,
        "track[sharing]": "private",  # publish last, after confirming upload
        "track[license]": "all-rights-reserved",
    }
    if bpm:
        fields["track[bpm]"] = str(int(bpm))
    if key:
        fields["track[key_signature]"] = key

    files = {
        "track[asset_data]": (
            audio_path.name,
            audio_path.read_bytes(),
            "audio/wav" if audio_path.suffix.lower() == ".wav" else "audio/mpeg",
        )
    }
    if artwork_path and artwork_path.exists():
        ctype = "image/jpeg" if artwork_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
        files["track[artwork_data]"] = (artwork_path.name, artwork_path.read_bytes(), ctype)

    log.info("Uploading '%s' to SoundCloud ...", title)
    result = _multipart_post(f"{SC_API_BASE}/tracks", token, fields, files)

    track_id = result.get("id")
    track_url = result.get("permalink_url", "")
    log.info("Track uploaded: id=%s url=%s (currently private)", track_id, track_url)

    # Now set to public
    log.info("Setting track to public ...")
    _sc_patch(f"{SC_API_BASE}/tracks/{track_id}", token, {"track[sharing]": "public"})
    log.info("Track is now public: %s", track_url)
    return track_url


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Upload a track to SoundCloud.")
    p.add_argument("--song-slug", required=True, help="Song slug from songs.json")
    p.add_argument("--audio", type=Path, help="Local audio file (WAV or MP3)")
    p.add_argument("--gcs-audio", help="GCS path to audio file (pulled to temp dir)")
    p.add_argument("--artwork", type=Path, help="Local cover art (JPEG/PNG)")
    p.add_argument("--gcs-artwork", help="GCS path to cover art")
    p.add_argument("--copy", type=Path, help="Release copy .md file for description")
    p.add_argument("--dry-run", action="store_true", help="Print what would happen without uploading")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    client_id = _require_env("SOUNDCLOUD_CLIENT_ID")
    client_secret = _require_env("SOUNDCLOUD_CLIENT_SECRET")
    song = _get_song(args.song_slug)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Resolve audio
        if args.audio:
            audio_path = args.audio
        elif args.gcs_audio:
            audio_path = tmp / Path(args.gcs_audio).name
            _pull_from_gcs(args.gcs_audio, audio_path)
        else:
            log.error("Provide --audio or --gcs-audio.")
            sys.exit(1)

        if not audio_path.exists():
            log.error("Audio file not found: %s", audio_path)
            sys.exit(1)

        # Resolve artwork (optional)
        artwork_path: Path | None = None
        if args.artwork:
            artwork_path = args.artwork
        elif args.gcs_artwork:
            artwork_path = tmp / Path(args.gcs_artwork).name
            _pull_from_gcs(args.gcs_artwork, artwork_path)

        # Resolve description
        description = ""
        if args.copy and args.copy.exists():
            description = _extract_description(args.copy)
        else:
            description = (
                f"{song.get('title', args.song_slug)}\n\n"
                "Produced by Dave Arnold\n"
                "Brainstorm + Sonic Spec: Gemini\n"
                "Session Partner: GitHub Copilot (Arc)\n"
                "Vocals: VELA (ElevenLabs)\n\n"
                "Process documented at: github.com/djaboxx/iron-static"
            )

        if not args.dry_run:
            token = _get_access_token(client_id, client_secret)
        else:
            token = "dry-run-token"

        url = upload(song, audio_path, artwork_path, description, token, args.dry_run)
        if url:
            log.info("SoundCloud URL: %s", url)


if __name__ == "__main__":
    main()
