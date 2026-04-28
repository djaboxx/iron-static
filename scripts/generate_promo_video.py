#!/usr/bin/env python3
"""
generate_promo_video.py — Veo 3 video generator for IRON STATIC.

Uses Google Veo 3 (via the google-genai SDK) to generate short-form promo videos
for the active song. Reads the brainstorm and song context from database/songs.json.
Supports text-to-video and image-to-video (pass --image to animate a cover art PNG).

Video generation is async: the script submits a job, polls until done, then saves
the output MP4 to outputs/social/.

Models:
  veo-3.0-generate-preview   Veo 3 (default) — best motion, 5–8s, optional AI audio
  veo-2.0-generate-001       Veo 2 — faster, cheaper, no AI audio

Output paths:
  outputs/social/<slug>_veo_landscape_v1.mp4   — 1920×1080 / 16:9
  outputs/social/<slug>_veo_square_v1.mp4      — 1080×1080 / 1:1
  outputs/social/<slug>_veo_portrait_v1.mp4    — 1080×1920 / 9:16

Usage:
  python scripts/generate_promo_video.py
  python scripts/generate_promo_video.py --song recorder-ui --format portrait
  python scripts/generate_promo_video.py --image outputs/social/recorder-ui_cover_square.png
  python scripts/generate_promo_video.py --style "corroded iron filaments dissolving into static" --count 2
  python scripts/generate_promo_video.py --dry-run   # print prompt only
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
SONGS_PATH = REPO_ROOT / "database" / "songs.json"
SOCIAL_OUT = REPO_ROOT / "outputs" / "social"

DEFAULT_MODEL = "veo-3.0-generate-preview"
FALLBACK_MODEL = "veo-2.0-generate-001"

# Format → Veo aspect_ratio string
FORMAT_ASPECT = {
    "landscape": "16:9",
    "square":    "1:1",
    "portrait":  "9:16",
}

# Veo generation constraints
MIN_DURATION = 5
MAX_DURATION = 8
DEFAULT_DURATION = 8

# Poll interval and timeout
POLL_INTERVAL_SECONDS = 15
POLL_TIMEOUT_SECONDS = 600  # 10 minutes

# Aesthetic constraints — mirrors generate_promo_image.py BASE_STYLE
BASE_VIDEO_STYLE = (
    "dark industrial aesthetic, high contrast, no people, no faces, "
    "machine textures, rust and corroded metal, electronic components in motion, "
    "harsh cold lighting, black background with electric blue accent colors, "
    "cinematic slow motion, photorealistic not illustrated"
)

NEGATIVE_PROMPT = (
    "people, faces, hands, bright colors, cheerful, pastel, nature, animals, "
    "cartoon, anime, illustrated, stock video, stage lighting, warm tones, "
    "DJ equipment, guitar, generic music video cliches"
)


# ---------------------------------------------------------------------------
# Song loading
# ---------------------------------------------------------------------------

def load_active_song() -> dict:
    with open(SONGS_PATH) as f:
        db = json.load(f)
    active = [s for s in db["songs"] if s.get("status") == "active"]
    if not active:
        raise RuntimeError(
            "No active song in database/songs.json. "
            "Run: python scripts/manage_songs.py activate --slug <slug>"
        )
    return active[0]


def load_song_by_slug(slug: str) -> dict:
    with open(SONGS_PATH) as f:
        db = json.load(f)
    matches = [s for s in db["songs"] if s["slug"] == slug]
    if not matches:
        raise RuntimeError(f"Song '{slug}' not found in database/songs.json")
    return matches[0]


def read_brainstorm(song: dict) -> str:
    brainstorm_path = song.get("brainstorm_path")
    if not brainstorm_path:
        return ""
    p = REPO_ROOT / brainstorm_path
    if not p.exists():
        log.warning("Brainstorm file not found: %s", p)
        return ""
    return p.read_text(encoding="utf-8")[:2000]


def build_video_prompt(song: dict, brainstorm: str, extra_style: str = "") -> str:
    """Build a Veo prompt grounded in the song's brainstorm and aesthetic."""
    key = song.get("key", "")
    scale = song.get("scale", "")
    title = song.get("title", song["slug"])

    # Extract first non-header line from brainstorm as creative seed
    seed_lines = [l.strip() for l in brainstorm.splitlines() if l.strip() and not l.startswith("#")]
    seed = seed_lines[0] if seed_lines else ""

    parts = [
        f"Short abstract promo video for '{title}' by IRON STATIC, an electronic metal band.",
        seed if seed else "Industrial electronic machine textures in motion.",
        f"Musical energy: {key} {scale} — heavy, mechanical, abrasive." if key else "",
        extra_style if extra_style else "",
        BASE_VIDEO_STYLE,
    ]
    prompt = " ".join(p for p in parts if p)
    log.debug("Video prompt: %s", prompt)
    return prompt


# ---------------------------------------------------------------------------
# Output path helpers
# ---------------------------------------------------------------------------

def next_output_path(slug: str, fmt: str) -> Path:
    """Return outputs/social/<slug>_veo_<format>_v<N>.mp4, incrementing N."""
    SOCIAL_OUT.mkdir(parents=True, exist_ok=True)
    n = 1
    while True:
        candidate = SOCIAL_OUT / f"{slug}_veo_{fmt}_v{n}.mp4"
        if not candidate.exists():
            return candidate
        n += 1


# ---------------------------------------------------------------------------
# Veo generation
# ---------------------------------------------------------------------------

def generate_video(
    prompt: str,
    song_slug: str,
    fmt: str,
    duration: int,
    count: int,
    image_path: Path | None,
    model: str,
    hd: bool,
    with_audio: bool,
    dry_run: bool,
) -> list[Path]:
    """Submit Veo job and poll until done. Returns list of saved output paths."""

    if dry_run:
        print(f"\n=== VIDEO PROMPT ({fmt}, {duration}s, {model}) ===")
        print(prompt)
        print(f"\n=== NEGATIVE PROMPT ===")
        print(NEGATIVE_PROMPT)
        if image_path:
            print(f"\nImage input: {image_path}")
        print(f"\nWould generate: {count} video(s) → outputs/social/{song_slug}_veo_{fmt}_v*.mp4")
        return []

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        log.error("Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")
        sys.exit(1)

    try:
        from google import genai
        from google.genai import types as gentypes
    except ImportError:
        log.error("google-genai not installed. Run: pip install google-genai")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # Build config
    cfg = gentypes.GenerateVideosConfig(
        number_of_videos=count,
        aspect_ratio=FORMAT_ASPECT[fmt],
        duration_seconds=duration,
        person_generation="dont_allow",
        negative_prompt=NEGATIVE_PROMPT,
    )

    # Optional image input for image-to-video
    image_input = None
    if image_path and image_path.exists():
        log.info("Image-to-video mode: %s", image_path)
        import mimetypes
        mime = mimetypes.guess_type(str(image_path))[0] or "image/png"
        image_input = gentypes.Image(image_bytes=image_path.read_bytes(), mime_type=mime)

    log.info(
        "Submitting Veo job: model=%s format=%s duration=%ds resolution=%s count=%d",
        model, fmt, duration, "1080p" if hd else "720p", count,
    )

    try:
        operation = client.models.generate_videos(
            model=model,
            prompt=prompt,
            image=image_input,
            config=cfg,
        )
    except Exception as exc:
        # If model not found, try fallback
        if "not found" in str(exc).lower() or "404" in str(exc) or "INVALID_ARGUMENT" in str(exc):
            log.warning("Model %s unavailable (%s), retrying with %s", model, exc, FALLBACK_MODEL)
            try:
                operation = client.models.generate_videos(
                    model=FALLBACK_MODEL,
                    prompt=prompt,
                    image=image_input,
                    config=cfg,
                )
            except Exception as exc2:
                log.error("Veo generation failed: %s", exc2)
                sys.exit(1)
        else:
            log.error("Veo generation failed: %s", exc)
            sys.exit(1)

    log.info("Job submitted (operation: %s). Polling every %ds...", operation.name, POLL_INTERVAL_SECONDS)

    # Poll until done
    deadline = time.time() + POLL_TIMEOUT_SECONDS
    while not operation.done:
        if time.time() > deadline:
            log.error("Timed out after %ds waiting for Veo job to complete.", POLL_TIMEOUT_SECONDS)
            sys.exit(1)
        time.sleep(POLL_INTERVAL_SECONDS)
        operation = client.operations.get(operation)
        log.info("Still generating... (done=%s)", operation.done)

    if operation.error:
        log.error("Veo job failed: %s", operation.error)
        sys.exit(1)

    if not operation.response or not operation.response.generated_videos:
        log.error("Veo job completed but returned no videos.")
        sys.exit(1)

    # Save outputs
    saved = []
    for i, gen_video in enumerate(operation.response.generated_videos):
        video = gen_video.video
        if not video:
            log.warning("No video object at index %d", i)
            continue

        out_path = next_output_path(song_slug, fmt)

        if video.video_bytes:
            out_path.write_bytes(video.video_bytes)
            log.info("Saved: %s (%d bytes)", out_path, len(video.video_bytes))
            saved.append(out_path)
        elif video.uri:
            # Video stored via Files API — download with API key auth
            log.info("Video at URI: %s — downloading...", video.uri)
            try:
                import urllib.request
                download_uri = video.uri
                if "key=" not in download_uri:
                    sep = "&" if "?" in download_uri else "?"
                    download_uri = f"{download_uri}{sep}key={api_key}"
                req = urllib.request.Request(download_uri, headers={"User-Agent": "iron-static/1.0"})
                with urllib.request.urlopen(req) as resp:
                    out_path.write_bytes(resp.read())
                log.info("Downloaded: %s", out_path)
                saved.append(out_path)
            except Exception as e:
                log.error("Failed to download video: %s", e)
        else:
            log.warning("Video at index %d has no bytes or URI.", i)

    return saved


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Veo 3 promo videos for IRON STATIC."
    )
    parser.add_argument(
        "--song",
        metavar="SLUG",
        help="Song slug from database/songs.json. Defaults to the active song.",
    )
    parser.add_argument(
        "--prompt",
        metavar="TEXT",
        default=None,
        help="Override the auto-generated prompt entirely.",
    )
    parser.add_argument(
        "--style",
        metavar="TEXT",
        default="",
        help="Extra style clause injected into the auto-generated prompt.",
    )
    parser.add_argument(
        "--image",
        metavar="PATH",
        default=None,
        help="Input image for image-to-video mode (animates a still, e.g. cover art PNG).",
    )
    parser.add_argument(
        "--format",
        dest="fmt",
        choices=list(FORMAT_ASPECT.keys()),
        default="landscape",
        help="Output aspect ratio. Default: landscape (16:9 for YouTube). Use portrait for Reels/TikTok.",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=DEFAULT_DURATION,
        metavar="SECONDS",
        help=f"Video duration in seconds ({MIN_DURATION}–{MAX_DURATION}). Default: {DEFAULT_DURATION}.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        metavar="N",
        help="Number of videos to generate (1–4). Default: 1.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        metavar="MODEL",
        help=f"Veo model to use. Default: {DEFAULT_MODEL}. Alternative: {FALLBACK_MODEL}.",
    )
    parser.add_argument(
        "--hd",
        action="store_true",
        help="Generate at 1080p instead of 720p. Costs more credits.",
    )
    parser.add_argument(
        "--with-audio",
        action="store_true",
        help="Let Veo 3 generate its own audio track (Veo 3 only). "
             "Default off — we use our own brand audio in post.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the prompt and config without calling the API.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    # Validate duration
    if not (MIN_DURATION <= args.duration <= MAX_DURATION):
        log.error("--duration must be between %d and %d seconds.", MIN_DURATION, MAX_DURATION)
        sys.exit(1)

    # Validate count
    if not (1 <= args.count <= 4):
        log.error("--count must be between 1 and 4.")
        sys.exit(1)

    # Load song context
    song = load_song_by_slug(args.song) if args.song else load_active_song()
    log.info("Song: %s (%s) — %s", song["title"], song["slug"], song.get("status"))

    # Build or use custom prompt
    if args.prompt:
        prompt = args.prompt
    else:
        brainstorm = read_brainstorm(song)
        prompt = build_video_prompt(song, brainstorm, args.style)

    # Resolve image input
    image_path = None
    if args.image:
        image_path = Path(args.image)
        if not image_path.is_absolute():
            image_path = REPO_ROOT / image_path
        if not image_path.exists():
            log.error("Image file not found: %s", image_path)
            sys.exit(1)

    # Generate
    saved = generate_video(
        prompt=prompt,
        song_slug=song["slug"],
        fmt=args.fmt,
        duration=args.duration,
        count=args.count,
        image_path=image_path,
        model=args.model,
        hd=args.hd,
        with_audio=args.with_audio,
        dry_run=args.dry_run,
    )

    if not args.dry_run:
        if saved:
            print("\nGenerated:")
            for path in saved:
                print(f"  {path}")
            print(
                "\nNext step: combine with brand audio using render_waveform_video.py, "
                "or post directly if --with-audio was used."
            )
        else:
            log.error("No videos were saved.")
            sys.exit(1)


if __name__ == "__main__":
    main()
