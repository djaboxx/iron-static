#!/usr/bin/env python3
"""
generate_caption.py — Gemini Flash caption generator for IRON STATIC social posts.

Reads the active song's brainstorm and metadata, then generates platform-appropriate
captions via Gemini Flash. Each platform has its own tone, length, and formatting rules.

Platforms:
  youtube     — Description field (up to 5000 chars). No hashtag spam.
  instagram   — 150 chars max visible, hashtags inline at end, up to 30 but we use ≤10.
  mastodon    — 500 char limit, short and sharp, ≤3 hashtags, feels like a post not an ad.
  soundcloud  — Track description, a bit longer, focus on the creative process.

Content types (--content-type):
  music       — Track or visualizer upload (default).
  vela        — Short VELA transmission / cold vocal fragment.
  manifesto   — Band philosophy or statement post paired with a visual.
  process     — Behind-the-scenes rig / session / patcher post.
  brainstorm  — Compelling idea surfaced from the Gemini brainstorm.

Output:
  outputs/social/<song-slug>_caption_<platform>.txt
  (or stdout with --stdout)

Usage:
  python scripts/generate_caption.py --song ignition-point --platform instagram
  python scripts/generate_caption.py --platform youtube --stdout
  python scripts/generate_caption.py --all-platforms
  python scripts/generate_caption.py --platform instagram --content-type vela
  python scripts/generate_caption.py --platform instagram --dry-run   # show prompt only
  python scripts/generate_caption.py --list-types
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

PLATFORMS = ["youtube", "instagram", "mastodon", "soundcloud"]

# ---------------------------------------------------------------------------
# Content types — what kind of post is this?
# ---------------------------------------------------------------------------

CONTENT_TYPES = {
    "music": {
        "label": "Music release / track upload",
        "suffix": (
            "This is a music post — a track or visualizer upload. "
            "Ground the caption in the song's sonic identity: "
            "key ({key} {scale}), BPM ({bpm}), the instrumentation described in the brainstorm, "
            "and any production decisions worth noting. The music is the subject."
        ),
    },
    "vela": {
        "label": "VELA transmission — short vocal fragment or statement",
        "suffix": (
            "This is a VELA post — a short transmission from IRON STATIC's vocalist. "
            "VELA is not human. She is cold, androgynous, declaratory. She transmits, not sings. "
            "The caption should feel like a system message or system alert wrapped in aesthetic intent. "
            "Short. Minimal. The caption IS the content. "
            "No hashtags about vocals or singers. VELA is a character, not a feature."
        ),
    },
    "manifesto": {
        "label": "Manifesto excerpt — band philosophy or statement post",
        "suffix": (
            "This is a manifesto post — a fragment of IRON STATIC's stated philosophy, "
            "paired with a visual. Extract one striking idea from the band context and write "
            "a caption that frames it as a declaration, not an explanation. "
            "Do not quote the manifesto directly — restate it in present tense, active voice. "
            "The visual carries the mood; the caption carries the idea."
        ),
    },
    "process": {
        "label": "Behind-the-scenes / rig / session post",
        "suffix": (
            "This is a process post — the rig, the session, the patcher, the hardware. "
            "Describe what is happening with technical specificity. "
            "Name the instruments. Name what they're doing. "
            "Make it interesting to someone who makes music, accessible to someone who doesn't. "
            "Heavy, weird, intentional — the process is part of the identity."
        ),
    },
    "brainstorm": {
        "label": "Brainstorm fragment — idea surfaced by Gemini",
        "suffix": (
            "This is a brainstorm post — a single compelling idea, phrase, or concept "
            "extracted from the most recent Gemini brainstorm. "
            "The caption should make the idea land as a standalone statement, "
            "as if it were the title of a song that doesn't exist yet. "
            "Make the reader curious about what IRON STATIC is working on without explaining it."
        ),
    },
}

DEFAULT_CONTENT_TYPE = "music"

# Per-platform instructions fed to Gemini
PLATFORM_SPECS = {
    "youtube": {
        "name": "YouTube",
        "max_chars": 5000,
        "instructions": (
            "Write a YouTube video description. "
            "2–4 sentences max. No 'excited to share' or 'drop everything'. "
            "Lead with what the track sounds like or does. "
            "End with: Produced by IRON STATIC. "
            "3–5 hashtags on a new line at the end: always include #IronStatic #ElectronicMetal. "
            "Hard limit: 5000 characters."
        ),
    },
    "instagram": {
        "name": "Instagram",
        "max_chars": 2200,
        "visible_chars": 125,  # chars before 'more' truncation
        "instructions": (
            "Write an Instagram caption for a heavy electronic music post. "
            "Structure: (1) A punchy opening hook of 1–2 sentences (≤125 chars total) — "
            "no hashtags in the hook. Draw directly from the song's concept, mood, or imagery "
            "described in the brainstorm. Sound like a musician with something to say, not a brand. "
            "(2) 2–4 sentences expanding on the track's themes, sounds, or process. "
            "Reference specific sonic/conceptual details from the brainstorm context. "
            "No 'dropping soon', 'excited to share', or hype language. "
            "(3) A blank line, then 8–12 hashtags: always include #IronStatic #ElectronicMetal "
            "#IndustrialMetal #HeavyElectronic — add 4–6 genre/mood-specific tags from the track context. "
            "Total length ≤2200 chars."
        ),
    },
    "mastodon": {
        "name": "Mastodon",
        "max_chars": 500,
        "instructions": (
            "Write a Mastodon post. Direct, blunt, no marketing language. "
            "Sound like a musician, not a brand. 1–2 sentences. "
            "≤3 hashtags: always #ironstaticband, pick 1–2 others relevant to the sound. "
            "Hard limit: 500 characters."
        ),
    },
    "soundcloud": {
        "name": "SoundCloud",
        "max_chars": 3000,
        "instructions": (
            "Write a SoundCloud track description. "
            "3–5 sentences. Focus on how it was made — instruments, key, scale, process. "
            "Reference the actual hardware if relevant (Digitakt, Rev2, DFAM, Subharmonicon, etc). "
            "No hyperbole. End with: IRON STATIC — [song title]. "
            "No hashtags in SoundCloud description."
        ),
    },
}


def load_active_song() -> dict:
    with open(SONGS_PATH) as f:
        db = json.load(f)
    active = [s for s in db["songs"] if s.get("status") == "active"]
    if not active:
        raise RuntimeError("No active song in database/songs.json.")
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
    return p.read_text(encoding="utf-8")[:3000]


def read_session_notes(song: dict) -> str:
    """Read the most recent session notes for this song, if any."""
    session_dir = REPO_ROOT / "knowledge" / "sessions"
    if not session_dir.exists():
        return ""
    slug = song["slug"]
    # Find session files containing the song slug, newest first
    matches = sorted(session_dir.glob(f"*{slug}*.md"), reverse=True)
    if matches:
        return matches[0].read_text(encoding="utf-8")[:2000]
    return ""


def build_caption_prompt(
    song: dict,
    platform: str,
    brainstorm: str,
    session_notes: str,
    content_type: str = DEFAULT_CONTENT_TYPE,
) -> str:
    spec = PLATFORM_SPECS[platform]
    title = song.get("title", song["slug"])
    key = song.get("key", "")
    scale = song.get("scale", "")
    bpm = song.get("bpm", "")

    # Inject content-type-specific instructions
    ctype = CONTENT_TYPES.get(content_type, CONTENT_TYPES[DEFAULT_CONTENT_TYPE])
    content_type_block = ctype["suffix"].format(
        key=key or "?",
        scale=scale or "",
        bpm=bpm or "?",
    )

    context_parts = [
        f"Song: '{title}' by IRON STATIC",
        f"Key: {key} {scale}".strip() if key else "",
        f"BPM: {bpm}" if bpm else "",
        f"Brainstorm seed:\n{brainstorm}" if brainstorm else "",
        f"Session notes:\n{session_notes}" if session_notes else "",
    ]
    context = "\n".join(p for p in context_parts if p)

    prompt = (
        f"CONTENT TYPE: {ctype['label']}\n{content_type_block}\n\n"
        f"{spec['instructions']}\n\n"
        f"Context about the track:\n{context}\n\n"
        f"Write only the caption. No preamble, no quotes around it, no explanation."
    )
    return prompt


def generate_caption_for_platform(
    song: dict,
    platform: str,
    brainstorm: str,
    session_notes: str,
    dry_run: bool,
    content_type: str = DEFAULT_CONTENT_TYPE,
) -> str | None:
    spec = PLATFORM_SPECS[platform]
    prompt = build_caption_prompt(song, platform, brainstorm, session_notes, content_type)

    if dry_run:
        print(f"\n=== PROMPT FOR {spec['name'].upper()} ===")
        print(prompt)
        return None

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
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=gentypes.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=4096,
        ),
    )
    caption = response.text.strip()

    # Enforce hard char limits
    max_chars = spec.get("max_chars")
    if max_chars and len(caption) > max_chars:
        log.warning("%s caption is %d chars (limit %d) — truncating", platform, len(caption), max_chars)
        caption = caption[:max_chars]

    return caption


def save_caption(song_slug: str, platform: str, caption: str) -> Path:
    SOCIAL_OUT.mkdir(parents=True, exist_ok=True)
    out_path = SOCIAL_OUT / f"{song_slug}_caption_{platform}.txt"
    out_path.write_text(caption, encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate platform-appropriate captions for IRON STATIC social posts."
    )
    parser.add_argument(
        "--song",
        metavar="SLUG",
        help="Song slug. Defaults to the active song.",
    )
    parser.add_argument(
        "--platform",
        choices=PLATFORMS,
        help="Single platform to generate for.",
    )
    parser.add_argument(
        "--all-platforms",
        action="store_true",
        help="Generate captions for all platforms.",
    )
    parser.add_argument(
        "--content-type",
        choices=list(CONTENT_TYPES.keys()),
        default=DEFAULT_CONTENT_TYPE,
        dest="content_type",
        help=(
            f"What type of content is being posted (default: {DEFAULT_CONTENT_TYPE}). "
            "Use --list-types for descriptions."
        ),
    )
    parser.add_argument(
        "--list-types",
        action="store_true",
        help="List available content types and exit.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print caption(s) to stdout instead of saving to files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show prompts without calling the API.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    if not args.platform and not args.all_platforms and not args.list_types:
        parser.error("Specify --platform <name>, --all-platforms, or --list-types")

    if args.list_types:
        print("Available content types (--content-type):")
        for key, val in CONTENT_TYPES.items():
            print(f"  {key:12s}  {val['label']}")
        return

    target_platforms = PLATFORMS if args.all_platforms else [args.platform]

    song = load_song_by_slug(args.song) if args.song else load_active_song()
    log.info("Song: %s (%s)", song["title"], song["slug"])

    brainstorm = read_brainstorm(song)
    session_notes = read_session_notes(song)

    for platform in target_platforms:
        caption = generate_caption_for_platform(
            song, platform, brainstorm, session_notes, args.dry_run,
            content_type=args.content_type,
        )
        if caption is None:
            continue  # dry run already printed prompt

        spec = PLATFORM_SPECS[platform]
        if args.stdout:
            print(f"\n{'='*50}")
            print(f"  {spec['name'].upper()} ({len(caption)} chars)")
            print(f"{'='*50}")
            print(caption)
        else:
            out_path = save_caption(song["slug"], platform, caption)
            log.info("Saved %s caption → %s (%d chars)", spec["name"], out_path, len(caption))
            print(f"  {platform:12s}  {out_path}  ({len(caption)} chars)")


if __name__ == "__main__":
    main()
