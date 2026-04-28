#!/usr/bin/env python3
"""
post_instagram.py — Instagram Content Publishing API client for IRON STATIC.

Posts images, Reels (video), and profile photo updates to an Instagram Professional
account via the Meta Graph API Content Publishing flow:
  Step 1: Upload file to GCS (public URL required by Meta)
  Step 2: Create a media container (POST /{user_id}/media)
  Step 3: Publish the container (POST /{user_id}/media_publish)

For Reels: uses media_type=REELS with video_url.
For profile photo: uses POST /{page_id}/picture (requires FACEBOOK_PAGE_ID env var).

The file must be a publicly accessible URL. This script uploads the local file
to GCS first, then uses the GCS public URL.

Requirements:
  - Instagram Professional account (Business or Creator)
  - Connected to a Facebook Page
  - Meta app with instagram_content_publish permission approved
  - Long-lived User Access Token (valid ~60 days; refresh before expiry)

Environment variables (required):
  INSTAGRAM_ACCESS_TOKEN   — long-lived user access token from Meta app
  INSTAGRAM_USER_ID        — numeric Instagram user ID (not username)
  GCS_BUCKET               — bucket name (for file hosting; already used by gcs_sync.py)
  GCS_SA_KEY               — service account JSON key (already used by gcs_sync.py)
  FACEBOOK_PAGE_ID         — (optional) Facebook Page ID for profile photo updates

Usage:
  python scripts/post_instagram.py --image outputs/social/IC_square.png --caption-file outputs/social/IC_caption_instagram.txt
  python scripts/post_instagram.py --song instrumental-convergence   # auto-resolve image + caption
  python scripts/post_instagram.py --reel outputs/social/recorder-ui_square.mp4 --caption-file outputs/social/recorder-ui_caption_instagram.txt
  python scripts/post_instagram.py --update-profile-photo outputs/social/brand_profile_2026.png
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
SUPPORTED_VIDEO_FORMATS = {".mp4", ".mov"}
MAX_REEL_BYTES = 1 * 1024 * 1024 * 1024  # 1 GB Instagram limit

# Caption file metadata header separator (lines up to and including second '---' are stripped)
CAPTION_HEADER_SEP = "---"

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

def _upload_to_gcs(file_path: Path, content_type: str = "image/jpeg") -> str:
    """Upload a file to GCS and return the public URL.

    Uploads to social/<filename> prefix in the bucket.
    """
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

    blob_name = f"social/{file_path.name}"
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(file_path), content_type=content_type)

    public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
    log.info("Uploaded to GCS: %s", public_url)
    return public_url


# ---------------------------------------------------------------------------
# Core publishing flow
# ---------------------------------------------------------------------------

def create_container(user_id: str, media_url: str, caption: str, access_token: str,
                     dry_run: bool, media_type: str = "IMAGE") -> str:
    """Step 1: Create a media container. Returns container ID."""
    log.info("Creating %s media container: %s", media_type, media_url)
    if dry_run:
        log.info("[DRY RUN] POST /%s/media  media_type=%s  url=%s  caption=%.80s...",
                 user_id, media_type, media_url, caption)
        return "DRY_RUN_CONTAINER_ID"

    params: dict = {"caption": caption, "access_token": access_token}
    if media_type == "REELS":
        params["media_type"] = "REELS"
        params["video_url"] = media_url
        params["share_to_feed"] = "true"
    else:
        params["image_url"] = media_url

    result = _graph_post(f"/{user_id}/media", params)
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
# Profile photo update
# ---------------------------------------------------------------------------

def update_profile_photo(photo_path: Path, access_token: str, dry_run: bool) -> None:
    """Update Instagram profile photo via the linked Facebook Page.

    Requires FACEBOOK_PAGE_ID env var. The Page profile picture syncs to Instagram.
    Needs pages_manage_posts or pages_manage_engagement permission.
    """
    page_id = _get_env("FACEBOOK_PAGE_ID")
    if not page_id:
        log.error("FACEBOOK_PAGE_ID env var required for profile photo update.")
        sys.exit(1)

    log.info("Uploading profile photo to GCS ...")
    if dry_run:
        photo_url = f"https://storage.googleapis.com/dry-run/social/{photo_path.name}"
        log.info("[DRY RUN] Would upload to GCS: %s", photo_url)
    else:
        photo_url = _upload_to_gcs(photo_path, content_type="image/png")

    log.info("Setting Facebook Page profile picture (will sync to Instagram) ...")
    if dry_run:
        log.info("[DRY RUN] POST /%s/picture  url=%s", page_id, photo_url)
        return

    result = _graph_post(f"/{page_id}/picture", {
        "url": photo_url,
        "access_token": access_token,
    })
    if "error" in result:
        log.error("Profile photo update failed: %s", result["error"].get("message"))
        sys.exit(1)
    log.info("Profile photo updated. Result: %s", result)


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


def _strip_caption_header(text: str) -> str:
    """Strip the metadata header block (lines up to and including second '---') from caption text."""
    lines = text.splitlines()
    sep_count = 0
    for i, line in enumerate(lines):
        if line.strip().startswith(CAPTION_HEADER_SEP):
            sep_count += 1
            if sep_count >= 2:
                return "\n".join(lines[i + 1:]).strip()
    return text.strip()


def _resolve_caption(args, song: dict | None, image_path: Path) -> str:
    # Explicit caption file
    if args.caption_file:
        p = Path(args.caption_file)
        if not p.is_absolute():
            p = REPO_ROOT / p
        if p.exists():
            return _strip_caption_header(p.read_text(encoding="utf-8"))
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
            return _strip_caption_header(candidate.read_text(encoding="utf-8"))
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


def _validate_image(image_path: Path) -> Path:
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


def _validate_reel(video_path: Path) -> Path:
    """Validate video meets Instagram Reel requirements."""
    if video_path.suffix.lower() not in SUPPORTED_VIDEO_FORMATS:
        log.error("Unsupported video format: %s. Supported: %s", video_path.suffix, SUPPORTED_VIDEO_FORMATS)
        sys.exit(1)
    size = video_path.stat().st_size
    if size > MAX_REEL_BYTES:
        log.error("Video exceeds 1GB limit: %d bytes", size)
        sys.exit(1)
    return video_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Post images, Reels, or update profile photo on Instagram.")
    parser.add_argument("--song", help="Song slug (auto-resolves image + caption for that song).")
    parser.add_argument("--image", help="Path to the image file to post (PNG or JPEG).")
    parser.add_argument("--reel", help="Path to the MP4 video file to post as a Reel.")
    parser.add_argument("--update-profile-photo", metavar="PHOTO",
                        help="Path to image to set as Instagram profile photo (requires FACEBOOK_PAGE_ID).")
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

    # --- Profile photo update (independent of post flow) ---
    if args.update_profile_photo:
        photo_path = Path(args.update_profile_photo)
        if not photo_path.is_absolute():
            photo_path = REPO_ROOT / photo_path
        if not photo_path.exists():
            log.error("Profile photo not found: %s", photo_path)
            sys.exit(1)
        update_profile_photo(photo_path, access_token, args.dry_run)
        if not args.reel and not args.image and not args.song:
            return  # profile-photo-only run

    # --- Reel posting ---
    if args.reel:
        reel_path = Path(args.reel)
        if not reel_path.is_absolute():
            reel_path = REPO_ROOT / reel_path
        if not reel_path.exists():
            log.error("Reel video not found: %s", reel_path)
            sys.exit(1)
        reel_path = _validate_reel(reel_path)
        caption = _resolve_caption(args, None, reel_path)

        log.info("Reel: %s", reel_path)
        log.info("Caption (%d chars): %.120s ...", len(caption), caption)

        if args.dry_run:
            _bucket = os.environ.get("GCS_BUCKET", "iron-static-files")
            video_url = f"https://storage.googleapis.com/{_bucket}/social/{reel_path.name}"
            log.info("[DRY RUN] Would upload to GCS: %s", video_url)
        else:
            video_url = _upload_to_gcs(reel_path, content_type="video/mp4")

        container_id = create_container(user_id, video_url, caption, access_token,
                                        args.dry_run, media_type="REELS")
        wait_for_container(container_id, access_token, args.dry_run)
        media_id = publish_container(user_id, container_id, access_token, args.dry_run)

        if not args.dry_run:
            log.info("Reel posted to Instagram. Media ID: %s", media_id)
            log.info("View at: https://www.instagram.com/")
            # Log media ID
            log_path = reel_path.parent / f"{reel_path.stem}_post_log.txt"
            log_path.write_text(f"media_id={media_id}\nposted_at={time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
            log.info("Logged to: %s", log_path)
        else:
            log.info("[DRY RUN] Complete. No Reel was posted.")
        return

    # --- Image posting (original flow) ---
    song = _load_song(args.song)
    if song is None and not args.image:
        log.error("No active song and no --image or --reel specified.")
        sys.exit(1)

    image_path = _resolve_image(args, song)
    image_path = _validate_image(image_path)  # may convert PNG→JPEG
    caption = _resolve_caption(args, song, image_path)

    log.info("Song: %s", song["title"] if song else "(none)")
    log.info("Image: %s", image_path)
    log.info("Caption (%d chars): %.120s ...", len(caption), caption)

    if args.dry_run:
        _bucket = os.environ.get("GCS_BUCKET", "iron-static-files")
        image_url = f"https://storage.googleapis.com/{_bucket}/social/{image_path.name}"
        log.info("[DRY RUN] Would upload to GCS: %s", image_url)
    else:
        image_url = _upload_to_gcs(image_path)

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
