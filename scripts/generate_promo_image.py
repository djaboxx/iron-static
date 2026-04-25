#!/usr/bin/env python3
"""
generate_promo_image.py — Gemini Imagen 3 promo image generator for IRON STATIC.

Reads the active song's brainstorm and key/scale/BPM from database/songs.json,
builds a dark industrial image prompt grounded in the brainstorm language,
and generates cover art / promo images at multiple aspect ratios.

Outputs:
  outputs/social/<song-slug>_cover_square.png      — 1:1  (Instagram, SoundCloud)
  outputs/social/<song-slug>_cover_landscape.png   — 16:9 (YouTube thumbnail)
  outputs/social/<song-slug>_cover_portrait.png    — 9:16 (Instagram Reels, TikTok)

Usage:
  python scripts/generate_promo_image.py --song rust-protocol
  python scripts/generate_promo_image.py --song rust-protocol --style "corroded neon circuit board"
  python scripts/generate_promo_image.py --song rust-protocol --formats square landscape
  python scripts/generate_promo_image.py --song rust-protocol --dry-run   # show prompt only
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
SONGS_PATH = REPO_ROOT / "database" / "songs.json"
SOCIAL_OUT = REPO_ROOT / "outputs" / "social"

# Aspect ratio → Imagen parameter
ASPECT_RATIOS = {
    "square":    {"ratio": "1:1",   "suffix": "square",    "desc": "Instagram / SoundCloud"},
    "landscape": {"ratio": "16:9",  "suffix": "landscape", "desc": "YouTube thumbnail"},
    "portrait":  {"ratio": "9:16",  "suffix": "portrait",  "desc": "Instagram Reels / TikTok"},
}

# Base aesthetic constraints — never overridden by brainstorm content
BASE_STYLE = (
    "dark industrial aesthetic, high contrast, no people, no faces, "
    "machine textures, rust and metal, electronic components, "
    "harsh lighting, black background with accent colors, "
    "typographic treatment with band name IRON STATIC in industrial sans-serif font, "
    "photorealistic not illustrated, cinematic composition"
)

NEGATIVE_PROMPT = (
    "colorful, bright, cheerful, happy, soft, pastel, nature, animals, "
    "people, faces, hands, cartoon, anime, illustrated, watercolor, "
    "stock photo, cliche music imagery, guitar, DJ equipment, stage lighting"
)


def load_active_song() -> dict:
    with open(SONGS_PATH) as f:
        db = json.load(f)
    active = [s for s in db["songs"] if s.get("status") == "active"]
    if not active:
        raise RuntimeError("No active song in database/songs.json. Run: python scripts/manage_songs.py activate --slug <slug>")
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
    return p.read_text(encoding="utf-8")[:2000]  # cap at 2000 chars for prompt


def build_image_prompt(song: dict, brainstorm: str, extra_style: str = "") -> str:
    """Build the Imagen prompt from song context and brainstorm language."""
    key = song.get("key", "")
    scale = song.get("scale", "")
    title = song.get("title", song["slug"])

    # Extract the first non-empty paragraph from brainstorm as creative seed
    seed_lines = [l.strip() for l in brainstorm.splitlines() if l.strip() and not l.startswith("#")]
    seed = seed_lines[0] if seed_lines else ""

    parts = [
        f"Album artwork for '{title}' by IRON STATIC.",
        seed if seed else "Industrial electronic metal texture.",
        f"Musical character: {key} {scale} — heavy, mechanical, abrasive." if key else "",
        extra_style if extra_style else "",
        BASE_STYLE,
    ]
    prompt = " ".join(p for p in parts if p)
    log.debug("Image prompt: %s", prompt)
    return prompt


def generate_images(prompt: str, song_slug: str, formats: list[str], dry_run: bool) -> dict[str, Path]:
    """Call Gemini Imagen 3 for each requested format. Returns {format: output_path}."""
    if dry_run:
        log.info("DRY RUN — prompt:\n%s", prompt)
        log.info("Would generate: %s", formats)
        return {}

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
    SOCIAL_OUT.mkdir(parents=True, exist_ok=True)

    results = {}
    for fmt in formats:
        spec = ASPECT_RATIOS[fmt]
        out_path = SOCIAL_OUT / f"{song_slug}_cover_{spec['suffix']}.png"
        log.info("Generating %s image (%s) → %s", fmt, spec["ratio"], out_path)

        try:
            response = client.models.generate_images(
                model="imagen-3.0-generate-002",
                prompt=prompt,
                config=gentypes.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=spec["ratio"],
                    negative_prompt=NEGATIVE_PROMPT,
                    safety_filter_level="block_only_high",
                    person_generation="dont_allow",
                ),
            )
            if not response.generated_images:
                log.error("No image returned for format %s", fmt)
                continue

            image_bytes = response.generated_images[0].image.image_bytes
            out_path.write_bytes(image_bytes)
            log.info("Saved: %s (%d bytes)", out_path, len(image_bytes))
            results[fmt] = out_path

        except Exception as exc:
            log.error("Imagen generation failed for %s: %s", fmt, exc)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate promo images for IRON STATIC using Gemini Imagen 3."
    )
    parser.add_argument(
        "--song",
        metavar="SLUG",
        help="Song slug from database/songs.json. Defaults to the active song.",
    )
    parser.add_argument(
        "--style",
        metavar="TEXT",
        default="",
        help="Extra style keywords to inject into the image prompt.",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=list(ASPECT_RATIOS.keys()),
        default=list(ASPECT_RATIOS.keys()),
        help="Which aspect ratios to generate. Default: all three.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated prompt without calling the API.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    song = load_song_by_slug(args.song) if args.song else load_active_song()
    log.info("Song: %s (%s) — %s", song["title"], song["slug"], song.get("status"))

    if song.get("status") == "in-progress":
        log.warning(
            "Song status is 'in-progress'. Generating promo images for unreleased work. "
            "Pass --song explicitly to confirm intent."
        )

    brainstorm = read_brainstorm(song)
    prompt = build_image_prompt(song, brainstorm, args.style)

    if args.dry_run:
        print("\n=== IMAGE PROMPT ===")
        print(prompt)
        print("\n=== NEGATIVE PROMPT ===")
        print(NEGATIVE_PROMPT)
        print(f"\nWould generate formats: {args.formats}")
        return

    results = generate_images(prompt, song["slug"], args.formats, args.dry_run)

    if results:
        print("\nGenerated:")
        for fmt, path in results.items():
            spec = ASPECT_RATIOS[fmt]
            print(f"  {fmt:12s} ({spec['ratio']:5s})  {path}  — {spec['desc']}")
    else:
        log.error("No images were generated.")
        sys.exit(1)


if __name__ == "__main__":
    main()
