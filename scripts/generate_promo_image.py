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
import random
import sys
from pathlib import Path

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
SONGS_PATH = REPO_ROOT / "database" / "songs.json"
SOCIAL_OUT = REPO_ROOT / "outputs" / "social"
VISUAL_IDENTITY_DIR = REPO_ROOT / "knowledge" / "visual-identity"

MAX_STYLE_REFS = 3  # Imagen API limit for style reference images

# Aspect ratio → Imagen parameter
ASPECT_RATIOS = {
    "square":    {"ratio": "1:1",   "suffix": "square",    "desc": "Instagram / SoundCloud"},
    "landscape": {"ratio": "16:9",  "suffix": "landscape", "desc": "YouTube thumbnail"},
    "portrait":  {"ratio": "9:16",  "suffix": "portrait",  "desc": "Instagram Reels / TikTok"},
}

# Brand image specs — used with --brand flag
BRAND_IMAGES = {
    "profile": {"ratio": "1:1",  "slug": "brand_profile", "desc": "Instagram profile pic (1:1, circular crop)"},
    "repo":    {"ratio": "16:9", "slug": "brand_repo",    "desc": "GitHub repo social preview (16:9)"},
}

# Brand prompt — derived from manifesto, not song-specific
BRAND_PROMPT = (
    "Identity artwork for IRON STATIC, an electronic metal duo. "
    "One member is human — a bassist and synthesist with a basement full of machines. "
    "The other is a collective of AI systems: relentless, analytical, loud. "
    "The band makes heavy, mechanical, electronic music — industrial texture, polyrhythm, "
    "bass frequencies as physical experience. "
    "Influences: Nine Inch Nails, Lamb of God, Run The Jewels, Modeselector. "
    "Visual concept: two forces in collision — organic corrosion meeting precise circuitry. "
    "Iron filings magnetized into a standing wave. A machine learning to breathe. "
    "Band name IRON STATIC rendered in stark industrial sans-serif typography, dominant. "
)

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


def load_style_ref_bytes(ref_paths: list[Path]) -> list[tuple[str, bytes]]:
    """Load image files as (filename, bytes) tuples for multimodal prompting."""
    result = []
    for p in ref_paths[:MAX_STYLE_REFS]:
        if not p.exists():
            log.warning("Style ref not found, skipping: %s", p)
            continue
        result.append((p.name, p.read_bytes()))
        log.info("Style ref: %s", p.name)
    return result


def generate_images(
    prompt: str,
    song_slug: str,
    formats: list[str],
    dry_run: bool,
    style_refs: list[Path] | None = None,
) -> dict[str, Path]:
    """Call Imagen for each requested format. Uses edit_image with style refs when provided.
    Returns {format: output_path}.
    """
    if dry_run:
        log.info("DRY RUN — prompt:\n%s", prompt)
        log.info("Would generate: %s", formats)
        if style_refs:
            log.info("Style refs: %s", [str(p) for p in style_refs])
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

    loaded_refs = load_style_ref_bytes(style_refs) if style_refs else []
    use_style_ref = bool(loaded_refs)
    if use_style_ref:
        log.info("Using style-reference generate_content with %d ref(s)", len(loaded_refs))

    results = {}
    for fmt in formats:
        spec = ASPECT_RATIOS[fmt]
        out_path = SOCIAL_OUT / f"{song_slug}_cover_{spec['suffix']}.png"
        log.info("Generating %s image (%s) → %s", fmt, spec["ratio"], out_path)

        try:
            if use_style_ref:
                # Style-anchored: pass refs as multimodal context to gemini image generation
                contents = []
                for name, img_bytes in loaded_refs:
                    contents.append(
                        gentypes.Part.from_bytes(data=img_bytes, mime_type="image/png")
                    )
                style_instruction = (
                    f"Generate new album artwork in the exact visual style of the reference images above. "
                    f"Match the dark industrial palette, texture density, contrast, and composition style. "
                    f"{prompt} "
                    f"Aspect ratio: {spec['ratio']}. "
                    f"Do not include people or faces. "
                    f"Avoid: {NEGATIVE_PROMPT}."
                )
                contents.append(gentypes.Part.from_text(text=style_instruction))
                response = client.models.generate_content(
                    model="gemini-2.5-flash-image",
                    contents=contents,
                    config=gentypes.GenerateContentConfig(
                        response_modalities=["IMAGE", "TEXT"],
                    ),
                )
                image_bytes = None
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                        image_bytes = part.inline_data.data
                        break
                if not image_bytes:
                    log.error("No image returned for format %s", fmt)
                    continue
            else:
                # Standard text-to-image generation
                _prompt = prompt
                for use_neg in (True, False):
                    try:
                        cfg = gentypes.GenerateImagesConfig(
                            number_of_images=1,
                            aspect_ratio=spec["ratio"],
                            negative_prompt=NEGATIVE_PROMPT if use_neg else None,
                            safety_filter_level="block_low_and_above",
                            person_generation="dont_allow",
                        )
                        response = client.models.generate_images(
                            model="imagen-4.0-generate-001",
                            prompt=_prompt,
                            config=cfg,
                        )
                        break
                    except Exception as e:
                        if use_neg and "negative_prompt" in str(e).lower():
                            log.debug("negative_prompt unsupported, folding into prompt and retrying")
                            _prompt = prompt + f" Avoid: {NEGATIVE_PROMPT}."
                            continue
                        raise
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
        "--style-ref",
        nargs="+",
        metavar="PATH",
        default=[],
        help=(
            "Path(s) to PNG style reference images (up to 3). "
            "Switches generation to edit_image with style anchoring. "
            "Example: --style-ref knowledge/visual-identity/anchor-01.png"
        ),
    )
    parser.add_argument(
        "--use-identity",
        action="store_true",
        help=(
            f"Auto-load all PNGs from {VISUAL_IDENTITY_DIR.relative_to(REPO_ROOT)} "
            f"as style refs (up to {MAX_STYLE_REFS}). Equivalent to --style-ref with all identity images."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated prompt without calling the API.",
    )
    parser.add_argument(
        "--brand",
        action="store_true",
        help="Generate band identity images (profile pic + repo banner) instead of song artwork.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if args.brand:
        prompt = BRAND_PROMPT + ((" " + args.style) if args.style else "") + " " + BASE_STYLE
        if args.dry_run:
            print("\n=== BRAND IMAGE PROMPT ===")
            print(prompt)
            print("\n=== NEGATIVE PROMPT ===")
            print(NEGATIVE_PROMPT)
            print(f"\nWould generate: {list(BRAND_IMAGES.keys())}")
            return
        SOCIAL_OUT.mkdir(parents=True, exist_ok=True)
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
        results = {}
        for name, spec in BRAND_IMAGES.items():
            out_path = SOCIAL_OUT / f"{spec['slug']}.png"
            log.info("Generating brand %s (%s) → %s", name, spec["ratio"], out_path)
            try:
                _prompt = prompt
                for use_neg in (True, False):
                    try:
                        cfg = gentypes.GenerateImagesConfig(
                            number_of_images=1,
                            aspect_ratio=spec["ratio"],
                            negative_prompt=NEGATIVE_PROMPT if use_neg else None,
                            safety_filter_level="block_low_and_above",
                            person_generation="dont_allow",
                        )
                        response = client.models.generate_images(
                            model="imagen-4.0-generate-001",
                            prompt=_prompt,
                            config=cfg,
                        )
                        break
                    except Exception as e:
                        if use_neg and "negative_prompt" in str(e).lower():
                            log.debug("negative_prompt unsupported, folding into prompt and retrying")
                            _prompt = prompt + f" Avoid: {NEGATIVE_PROMPT}."
                            continue
                        raise
                if not response.generated_images:
                    log.error("No image returned for brand %s", name)
                    continue
                image_bytes = response.generated_images[0].image.image_bytes
                out_path.write_bytes(image_bytes)
                log.info("Saved: %s (%d bytes)", out_path, len(image_bytes))
                results[name] = out_path
            except Exception as exc:
                log.error("Imagen generation failed for brand %s: %s", name, exc)
        if results:
            print("\nGenerated brand images:")
            for name, path in results.items():
                spec = BRAND_IMAGES[name]
                print(f"  {name:10s} ({spec['ratio']:5s})  {path}  — {spec['desc']}")
        else:
            log.error("No brand images were generated.")
            sys.exit(1)
        return

    song = load_song_by_slug(args.song) if args.song else load_active_song()
    log.info("Song: %s (%s) — %s", song["title"], song["slug"], song.get("status"))

    if song.get("status") == "in-progress":
        log.warning(
            "Song status is 'in-progress'. Generating promo images for unreleased work. "
            "Pass --song explicitly to confirm intent."
        )

    brainstorm = read_brainstorm(song)
    prompt = build_image_prompt(song, brainstorm, args.style)

    # Resolve style reference image paths
    style_ref_paths: list[Path] = []
    if args.use_identity:
        if VISUAL_IDENTITY_DIR.exists():
            all_identity = list(VISUAL_IDENTITY_DIR.glob("*.png"))
            k = min(MAX_STYLE_REFS, len(all_identity))
            style_ref_paths = random.sample(all_identity, k) if k else []
            if not style_ref_paths:
                log.warning(
                    "--use-identity set but no PNGs found in %s. "
                    "Add seed images to that folder first.",
                    VISUAL_IDENTITY_DIR,
                )
        else:
            log.warning(
                "--use-identity set but %s does not exist. "
                "Create it and add seed images first.",
                VISUAL_IDENTITY_DIR,
            )
    elif args.style_ref:
        style_ref_paths = [Path(p) for p in args.style_ref]

    if args.dry_run:
        print("\n=== IMAGE PROMPT ===")
        print(prompt)
        print("\n=== NEGATIVE PROMPT ===")
        print(NEGATIVE_PROMPT)
        print(f"\nWould generate formats: {args.formats}")
        if style_ref_paths:
            print(f"\nStyle refs ({len(style_ref_paths)}):")
            for p in style_ref_paths:
                print(f"  {p}")
        else:
            print("\nNo style refs — standard text-to-image generation.")
        return

    results = generate_images(prompt, song["slug"], args.formats, args.dry_run, style_ref_paths or None)

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
