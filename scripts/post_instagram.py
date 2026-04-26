#!/usr/bin/env python3
"""
post_instagram.py — Instagram Content Publishing API client for IRON STATIC.

Posts a single image with caption to an Instagram Professional account via the
Meta Graph API Content Publishing flow:
  Step 1: Create a media container (POST /{user_id}/media)
  Step 2: Publish the container (POST /{user_id}/media_publish)

The image must be a publicly accessible URL. This script uploads the local image
to GCS first (if it is not already a URL), then uses the GCS public URL.

Requirements:
  - Instagram Professional account (Business or Creator)
  - Connected to a Facebook Page
  - Meta app with instagram_content_publish permission approved
  - Long-lived User Access Token (valid ~60 days; refresh before expiry)

Environment variables (required):
  INSTAGRAM_ACCESS_TOKEN   — long-lived user access token from Meta app
  INSTAGRAM_USER_ID        — numeric Instagram user ID (not username)
  GCS_BUCKET               — bucket name (for image hosting; already used by gcs_sync.py)
  GCS_SA_KEY               — service account JSON key (already used by gcs_sync.py)

Usage:
  python scripts/post_instagram.py --image outputs/social/instrumental-convergence_cover_square.png
  python scripts/post_instagram.py --image outputs/social/IC_square.png --caption-file outputs/social/IC_caption_instagram.txt
  python scripts/post_instagram.py --song instrumental-convergence   # auto-resolve image + caption
  python scripts/post_instagram.py --image ... --dry-run             # print API calls without executing
  python scripts/post_instagram.py --check-token                     # verify token validity + expiry

Rate limit: 25 API-published posts per 24-hour rolling window per account.
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

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

REPO_ROOT = Path(__file__).resolve().parent.parent

# Load .env from repo root if present (never overrides existing env vars)
_env_file = REPO_ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())
SONGS_PATH = REPO_ROOT / "database" / "songs.json"
SOCIAL_OUT = REPO_ROOT / "outputs" / "social"

GRAPH_API_BASE = "https://graph.facebook.com/v22.0"

# Instagram image requirements (enforced server-side; stated here for early validation)
MAX_IMAGE_BYTES = 8 * 1024 * 1024   # 8 MB
SUPPORTED_FORMATS = {".jpg", ".jpeg"}

# Container status polling
CONTAINER_POLL_INTERVAL = 5   # seconds between status checks
CONTAINER_POLL_MAX = 12       # max attempts (60s total)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _get_env(name: str, required: bool = True) -> str:
    val = os.environ.get(name, "")
    if not val and required:
        log.error("Environment variable %s is not set.", name)
        sys.exit(1)
    return val


def _graph_get(path: str, params: dict) -> dict:
    query = urlencode(params)
    url = f"{GRAPH_API_BASE}{path}?{query}"
    req = Request(url, headers={"Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _graph_post(path: str, data: dict) -> dict:
    url = f"{GRAPH_API_BASE}{path}"
    body = urlencode(data).encode()
    req = Request(url, data=body, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    })
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


# ---------------------------------------------------------------------------
# Token check
# ---------------------------------------------------------------------------

def check_token(access_token: str) -> None:
    """Print token validity, scopes, and expiry date."""
    log.info("Checking token validity via /debug_token ...")
    data = _graph_get("/debug_token", {
        "input_token": access_token,
        "access_token": access_token,
    })
    info = data.get("data", {})
    if not info.get("is_valid"):
        log.error("Token is NOT valid. Error: %s", info.get("error", {}).get("message", "unknown"))
        sys.exit(1)

    import datetime
    expires_at = info.get("expires_at")
    if expires_at:
        exp_dt = datetime.datetime.fromtimestamp(expires_at)
        days_left = (exp_dt - datetime.datetime.now()).days
        log.info("Token valid. Expires: %s (%d days)", exp_dt.strftime("%Y-%m-%d"), days_left)
        if days_left < 7:
            log.warning("Token expires in %d days — refresh soon.", days_left)
    else:
        log.info("Token valid (no expiry — likely a system user token).")

    scopes = info.get("scopes", [])
    log.info("Scopes: %s", ", ".join(scopes))
    if "instagram_content_publish" not in scopes:
        log.error("Missing required scope: instagram_content_publish")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Image upload: local file → GCS public URL
# ---------------------------------------------------------------------------

def _upload_to_gcs(image_path: Path) -> str:
    """Upload image to GCS and return the public URL.

    Re-uses the gcs_sync.py GCS client infrastructure. Uploads to
    social/<filename> prefix in the bucket and returns the public URL.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "gcs_sync", REPO_ROOT / "scripts" / "gcs_sync.py"
    )
    if spec:
        gcs_sync = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gcs_sync)
    else:
        gcs_sync = None
    # Fallback: use google-cloud-storage directly
    try:
        from google.cloud import storage as gcs
    except ImportError:
        log.error("google-cloud-storage not installed. Run: pip install google-cloud-storage")
        sys.exit(1)

    bucket_name = _get_env("GCS_BUCKET")
    sa_key_json = os.environ.get("GCS_SA_KEY", "")

    if sa_key_json:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp.write(sa_key_json)
            tmp_path = tmp.name
        try:
            client = gcs.Client.from_service_account_json(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    else:
        client = gcs.Client()  # uses ADC

    blob_name = f"social/{image_path.name}"
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(image_path), content_type="image/jpeg")

    public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
    log.info("Uploaded to GCS: %s", public_url)
    return public_url


# ---------------------------------------------------------------------------
# Core publishing flow
# ---------------------------------------------------------------------------

def create_container(user_id: str, image_url: str, caption: str, access_token: str, dry_run: bool) -> str:
    """Step 1: Create a media container. Returns container ID."""
    log.info("Creating media container for image: %s", image_url)
    if dry_run:
        log.info("[DRY RUN] POST /%s/media  image_url=%s  caption=%.80s...", user_id, image_url, caption)
        return "DRY_RUN_CONTAINER_ID"

    result = _graph_post(f"/{user_id}/media", {
        "image_url": image_url,
        "caption": caption,
        "access_token": access_token,
    })
    if "error" in result:
        log.error("Container creation failed: %s", result["error"].get("message"))
        sys.exit(1)

    container_id = result.get("id")
    log.info("Container created: %s", container_id)
    return container_id


def wait_for_container(container_id: str, access_token: str, dry_run: bool) -> None:
    """Poll container status until FINISHED (or fail)."""
    if dry_run:
        return

    for attempt in range(CONTAINER_POLL_MAX):
        result = _graph_get(f"/{container_id}", {
            "fields": "status_code",
            "access_token": access_token,
        })
        status = result.get("status_code", "UNKNOWN")
        log.info("Container %s status: %s", container_id, status)
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            log.error("Container entered status %s. Cannot publish.", status)
            sys.exit(1)
        time.sleep(CONTAINER_POLL_INTERVAL)

    log.error("Container did not reach FINISHED after %ds. Aborting.", CONTAINER_POLL_INTERVAL * CONTAINER_POLL_MAX)
    sys.exit(1)


def publish_container(user_id: str, container_id: str, access_token: str, dry_run: bool) -> str:
    """Step 2: Publish the container. Returns the published media ID."""
    log.info("Publishing container %s ...", container_id)
    if dry_run:
        log.info("[DRY RUN] POST /%s/media_publish  creation_id=%s", user_id, container_id)
        return "DRY_RUN_MEDIA_ID"

    result = _graph_post(f"/{user_id}/media_publish", {
        "creation_id": container_id,
        "access_token": access_token,
    })
    if "error" in result:
        log.error("Publish failed: %s", result["error"].get("message"))
        sys.exit(1)

    media_id = result.get("id")
    log.info("Published. Instagram media ID: %s", media_id)
    return media_id


# ---------------------------------------------------------------------------
# Song / file resolution
# ---------------------------------------------------------------------------

def _load_song(slug: str | None) -> dict | None:
    with open(SONGS_PATH) as f:
        db = json.load(f)
    if slug:
        matches = [s for s in db["songs"] if s["slug"] == slug]
        return matches[0] if matches else None
    active = [s for s in db["songs"] if s.get("status") == "active"]
    return active[0] if active else None


def _resolve_image(args, song: dict | None) -> Path:
    if args.image:
        p = Path(args.image)
        if not p.is_absolute():
            p = REPO_ROOT / p
        if not p.exists():
            log.error("Image not found: %s", p)
            sys.exit(1)
        return p

    if song:
        slug = song["slug"]
        for fmt in ("square", "landscape", "portrait"):
            candidate = SOCIAL_OUT / f"{slug}_cover_{fmt}.png"
            if candidate.exists():
                log.info("Auto-resolved image: %s", candidate)
                return candidate
        log.error("No cover image found for song '%s' in %s", slug, SOCIAL_OUT)
        log.error("Run: python scripts/generate_promo_image.py --song %s", slug)
        sys.exit(1)

    log.error("No --image provided and no active song found.")
    sys.exit(1)


def _resolve_caption(args, song: dict | None, image_path: Path) -> str:
    # Explicit caption file
    if args.caption_file:
        p = Path(args.caption_file)
        if not p.is_absolute():
            p = REPO_ROOT / p
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
        log.error("Caption file not found: %s", p)
        sys.exit(1)

    # Explicit caption string
    if args.caption:
        return args.caption

    # Auto-resolve from social output dir
    if song:
        slug = song["slug"]
        candidate = SOCIAL_OUT / f"{slug}_caption_instagram.txt"
        if candidate.exists():
            log.info("Auto-resolved caption: %s", candidate)
            return candidate.read_text(encoding="utf-8").strip()
        log.warning("No caption file found. Generating one now ...")
        import subprocess
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "generate_caption.py"),
             "--song", slug, "--platform", "instagram"],
            capture_output=True, text=True, cwd=str(REPO_ROOT)
        )
        if result.returncode == 0 and candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()
        log.warning("Caption generation failed; posting without caption.")

    return ""


def _validate_image(image_path: Path) -> None:
    """Validate image meets Instagram requirements before uploading."""
    if image_path.suffix.lower() not in SUPPORTED_FORMATS:
        # Instagram requires JPEG. PNG files need conversion.
        log.warning(
            "Instagram requires JPEG. %s is %s — converting to JPEG.",
            image_path.name, image_path.suffix
        )
        try:
            from PIL import Image
            jpg_path = image_path.with_suffix(".jpg")
            img = Image.open(image_path).convert("RGB")
            img.save(jpg_path, "JPEG", quality=95)
            log.info("Converted to JPEG: %s", jpg_path)
            return jpg_path
        except ImportError:
            log.error("Pillow not installed and image is not JPEG. Run: pip install Pillow")
            sys.exit(1)

    size = image_path.stat().st_size
    if size > MAX_IMAGE_BYTES:
        log.error("Image exceeds 8MB limit: %d bytes", size)
        sys.exit(1)

    return image_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Post an image to Instagram via Meta Graph API.")
    parser.add_argument("--song", help="Song slug (auto-resolves image + caption for that song).")
    parser.add_argument("--image", help="Path to the image file to post (PNG or JPEG).")
    parser.add_argument("--caption", help="Caption text (overrides auto-resolve).")
    parser.add_argument("--caption-file", help="Path to a .txt file containing the caption.")
    parser.add_argument("--dry-run", action="store_true", help="Print API calls without executing.")
    parser.add_argument("--check-token", action="store_true", help="Verify token validity and exit.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Debug logging.")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    access_token = _get_env("INSTAGRAM_ACCESS_TOKEN")
    user_id = _get_env("INSTAGRAM_USER_ID")

    if args.check_token:
        check_token(access_token)
        return

    song = _load_song(args.song)
    if song is None and not args.image:
        log.error("No active song and no --image specified.")
        sys.exit(1)

    image_path = _resolve_image(args, song)
    image_path = _validate_image(image_path)  # may convert PNG→JPEG
    caption = _resolve_caption(args, song, image_path)

    log.info("Song: %s", song["title"] if song else "(none)")
    log.info("Image: %s", image_path)
    log.info("Caption (%d chars): %.120s ...", len(caption), caption)

    # Upload image to GCS to get a public URL
    if args.dry_run:
        _bucket = os.environ.get("GCS_BUCKET", "iron-static-files")
        image_url = f"https://storage.googleapis.com/{_bucket}/social/{image_path.name}"
        log.info("[DRY RUN] Would upload to GCS: %s", image_url)
    else:
        image_url = _upload_to_gcs(image_path)

    # Two-step: create container → publish
    container_id = create_container(user_id, image_url, caption, access_token, args.dry_run)
    wait_for_container(container_id, access_token, args.dry_run)
    media_id = publish_container(user_id, container_id, access_token, args.dry_run)

    if not args.dry_run:
        log.info("Posted to Instagram. Media ID: %s", media_id)
        log.info("View at: https://www.instagram.com/")
    else:
        log.info("[DRY RUN] Complete. No post was made.")


if __name__ == "__main__":
    main()
