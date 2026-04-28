#!/usr/bin/env python3
"""
storyboard_video.py — Multi-scene storyboard video pipeline for IRON STATIC.

Pipeline:
  1. Gemini 2.0 Flash  → generates N-scene storyboard JSON (description + image_prompt + animation_prompt per scene)
  2. Imagen 4          → renders a keyframe PNG for each scene
  3. Veo 2 (i2v)       → animates each keyframe into an 8s clip
  4. ffmpeg concat     → stitches all clips into one final MP4

Usage:
  python scripts/storyboard_video.py
  python scripts/storyboard_video.py --scenes 3 --format landscape
  python scripts/storyboard_video.py --seed-image outputs/social/ignition-point_cover_square.png
  python scripts/storyboard_video.py --director-note "focus on machine awakening arc"
  python scripts/storyboard_video.py --dry-run   # print storyboard only, no generation
"""

import argparse
import json
import logging
import mimetypes
import os
import re
import subprocess
import sys
import time
from pathlib import Path

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
SONGS_PATH = REPO_ROOT / "database" / "songs.json"
STYLE_PATH = REPO_ROOT / "database" / "visual-style.json"
SOCIAL_OUT = REPO_ROOT / "outputs" / "social"

STORYBOARD_MODEL = "gemini-2.5-flash"
IMAGE_MODEL      = "imagen-4.0-generate-001"
VIDEO_MODEL      = "veo-3.0-generate-preview"
VIDEO_FALLBACK   = "veo-2.0-generate-001"

FORMAT_ASPECT = {
    "landscape": "16:9",
    "square":    "1:1",
    "portrait":  "9:16",
}

POLL_INTERVAL = 15
POLL_TIMEOUT  = 480  # 8 min per scene

NEGATIVE_PROMPT = (
    "people, faces, hands, bright colors, cheerful, pastel, nature, animals, "
    "cartoon, anime, illustrated, stock video, stage lighting, warm tones, "
    "DJ equipment, guitar, generic music video cliches"
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    if not key:
        log.error("GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set.")
        sys.exit(1)
    return key


def load_active_song() -> dict:
    db = json.loads(SONGS_PATH.read_text())
    for s in db.get("songs", []):
        if s.get("status") == "active":
            return s
    return {}


def load_style() -> dict:
    if STYLE_PATH.exists():
        return json.loads(STYLE_PATH.read_text())
    return {}


def load_brainstorm(song: dict) -> str:
    bp = song.get("brainstorm_path", "")
    if not bp:
        return ""
    full = Path(bp) if Path(bp).is_absolute() else REPO_ROOT / bp
    if full.exists():
        return full.read_text()[:2000]
    return ""


def next_output_path(slug: str, prefix: str, fmt: str, ext: str) -> Path:
    SOCIAL_OUT.mkdir(parents=True, exist_ok=True)
    n = 1
    while True:
        p = SOCIAL_OUT / f"{slug}_{prefix}_{fmt}_v{n}.{ext}"
        if not p.exists():
            return p
        n += 1


# ─── Step 1: Storyboard via Gemini ────────────────────────────────────────────

def generate_storyboard(client, song: dict, brainstorm: str, style: dict,
                        num_scenes: int, fmt: str, director_note: str,
                        seed_image_name: str = "") -> dict:
    song_line = (
        f'"{song.get("title", "Unknown")}" by IRON STATIC — '
        f'{song.get("key", "")} {song.get("scale", "")} @ {song.get("bpm", "")}BPM'
        if song else "IRON STATIC brand video"
    )

    palette = style.get("palette", {})
    color_lang = (
        f'Background: {palette.get("background", {}).get("description", "void black")}. '
        f'Primary accent: {palette.get("primary_accent", {}).get("description", "cold cobalt-white")}. '
        f'Danger: {palette.get("secondary_accent", {}).get("description", "rust-orange")}.'
    )

    imagery_vocab = "; ".join(
        f'{v["name"]}: {v["description"]}'
        for v in style.get("imagery", {}).get("vocabulary", [])
    ) or "corroded metal, circuit traces, iron filings, electric discharge, smoke"

    seed_note = (
        f'\nSCENE 1 ANCHOR: The first scene will be animated from an existing image '
        f'"{seed_image_name}" — its image_prompt should describe this image accurately.'
        if seed_image_name else ""
    )

    prompt = f"""You are a creative director for IRON STATIC, a dark electronic-metal band. Generate a {num_scenes}-scene video storyboard as valid JSON.

SONG: {song_line}
FORMAT: {fmt}{seed_note}
{f"DIRECTOR NOTE: {director_note}" if director_note else ""}

VISUAL LANGUAGE:
Colors: {color_lang}
Imagery vocabulary: {imagery_vocab}
Motion: Imperceptibly slow camera. No cuts within clips. Photorealistic.
NEVER: people, faces, hands, warm colors, cartoon, anime.

BRAINSTORM CONTEXT:
{brainstorm or "Industrial electronic music — heavy machine energy, cold precision, controlled chaos."}

STORYBOARD RULES:
1. Scenes flow together — shared visual thread, each reveals something new
2. Arc: build tension → peak intensity → release or unresolved question
3. Each scene = a distinct LOCATION or PHASE within the same visual world
4. image_prompt: what Imagen 4 should render (150-200 words, photorealistic, still frame)
5. animation_prompt: what Veo 2 should animate (60-80 words MAX — shorter is better)
6. animation_prompt must describe MOTION ONLY of elements already in the image
7. Every animation_prompt ends with: "Camera holds still. No cuts. Extreme slow motion. Photorealistic."

Respond with ONLY valid JSON matching this exact schema — no markdown fences, no explanation:
{{
  "title": "short evocative title",
  "arc": "one sentence describing the emotional arc",
  "scenes": [
    {{
      "id": 1,
      "description": "25 words on the emotional/narrative purpose",
      "image_prompt": "...",
      "animation_prompt": "..."
    }}
  ]
}}"""

    response = client.models.generate_content(
        model=STORYBOARD_MODEL,
        contents=prompt,
        config={"temperature": 0.85, "maxOutputTokens": 8192, "thinkingConfig": {"thinkingBudget": 0}},
    )
    raw = getattr(response, "text", "") or ""
    # Strip markdown code fences if Gemini wraps it
    raw = re.sub(r"^```(?:json)?\n?", "", raw.strip())
    raw = re.sub(r"\n?```$", "", raw.strip())
    return json.loads(raw)


# ─── Step 2: Keyframe via Imagen 4 ────────────────────────────────────────────

def generate_keyframe(client, scene: dict, slug: str, aspect_ratio: str) -> Path:
    from google.genai import types as gentypes

    response = client.models.generate_images(
        model=IMAGE_MODEL,
        prompt=scene["image_prompt"],
        config=gentypes.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio=aspect_ratio,
            person_generation="dont_allow",
        ),
    )
    images = response.generated_images or []
    if not images:
        raise RuntimeError(f"Imagen returned no images for scene {scene['id']}")

    img_bytes = images[0].image.image_bytes
    out_path = SOCIAL_OUT / f"{slug}_storyboard_scene{scene['id']}.png"
    out_path.write_bytes(img_bytes)
    log.info("Keyframe saved: %s", out_path)
    return out_path


# ─── Step 3: Animate via Veo 2 (image-to-video) ───────────────────────────────

def animate_scene(client, scene: dict, image_path: Path,
                  slug: str, aspect_ratio: str, api_key: str) -> Path:
    from google.genai import types as gentypes

    mime = mimetypes.guess_type(str(image_path))[0] or "image/png"
    image_input = gentypes.Image(
        image_bytes=image_path.read_bytes(),
        mime_type=mime,
    )

    cfg = gentypes.GenerateVideosConfig(
        number_of_videos=1,
        aspect_ratio=aspect_ratio,
        duration_seconds=8,
        person_generation="dont_allow",
    )

    operation = None
    used_model = VIDEO_FALLBACK
    for model in [VIDEO_MODEL, VIDEO_FALLBACK]:
        try:
            log.info("Submitting Veo job (scene %d) with model %s ...", scene["id"], model)
            operation = client.models.generate_videos(
                model=model,
                prompt=scene["animation_prompt"],
                image=image_input,
                config=cfg,
            )
            used_model = model
            break
        except Exception as exc:
            msg = str(exc)
            if "not found" in msg.lower() or "404" in msg or "INVALID_ARGUMENT" in msg:
                log.warning("Model %s unavailable, trying fallback...", model)
                continue
            raise

    if operation is None:
        raise RuntimeError("No Veo model available")

    log.info("Job submitted (scene %d, model=%s). Polling every %ds ...", scene["id"], used_model, POLL_INTERVAL)
    deadline = time.time() + POLL_TIMEOUT
    while not operation.done:
        if time.time() > deadline:
            raise TimeoutError(f"Scene {scene['id']} timed out after {POLL_TIMEOUT}s")
        time.sleep(POLL_INTERVAL)
        operation = client.operations.get(operation)
        log.info("Scene %d: still generating...", scene["id"])

    if operation.error:
        raise RuntimeError(f"Veo error on scene {scene['id']}: {operation.error}")

    videos = getattr(operation.response, "generated_videos", None) or []

    if not videos:
        raise RuntimeError(f"Veo returned no videos for scene {scene['id']}")

    gen_video = videos[0]
    video = gen_video.video
    out_path = SOCIAL_OUT / f"{slug}_storyboard_scene{scene['id']}.mp4"

    if video.video_bytes:
        out_path.write_bytes(video.video_bytes)
    elif video.uri:
        import urllib.request
        uri = video.uri
        sep = "&" if "?" in uri else "?"
        url = f"{uri}{sep}key={api_key}"
        log.info("Downloading from URI: %s", uri)
        req = urllib.request.Request(url, headers={"User-Agent": "iron-static/1.0"})
        with urllib.request.urlopen(req) as resp:
            out_path.write_bytes(resp.read())
    else:
        raise RuntimeError(f"Scene {scene['id']}: no video bytes or URI in response")

    log.info("Clip saved: %s", out_path)
    return out_path


# ─── Step 4: ffmpeg stitch (concat or xfade) ─────────────────────────────────

# Available xfade transitions (subset — all work in ffmpeg ≥ 4.3)
XFADE_TRANSITIONS = [
    "fade", "fadeblack", "fadewhite", "dissolve", "pixelize",
    "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown",
    "radial", "circleopen", "circleclose",
    "hblur", "hlslice", "hrslice", "vuslice", "vdslice",
    "zoomin", "squeezev", "squeezeh",
]


def concat_clips(
    clip_paths: list,
    slug: str,
    fmt: str,
    transition: str = "none",
    transition_duration: float = 0.5,
) -> Path:
    """Stitch clips together.

    transition='none'  — fast stream-copy concat (original behaviour)
    transition=<name>  — ffmpeg xfade filter; re-encodes with libx264/aac.
                         Any name from XFADE_TRANSITIONS is valid, plus 'none'.
    transition_duration — overlap length in seconds (default 0.5).
    """
    out_path = next_output_path(slug, "storyboard", fmt, "mp4")

    if transition == "none" or len(clip_paths) < 2:
        # Fast path: stream-copy concat demuxer
        list_path = SOCIAL_OUT / f"{slug}_concat_list.txt"
        list_path.write_text("\n".join(f"file '{p}'" for p in clip_paths))
        result = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(list_path), "-c", "copy", str(out_path)],
            capture_output=True, text=True,
        )
        list_path.unlink(missing_ok=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg concat failed: {result.stderr[-500:]}")
    else:
        # xfade path: build filter_complex chain
        # Each clip must be probed for its duration so offsets are exact.
        durations = []
        for p in clip_paths:
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(p)],
                capture_output=True, text=True,
            )
            try:
                durations.append(float(probe.stdout.strip()))
            except ValueError:
                durations.append(8.0)  # fallback if probe fails

        td = transition_duration
        n = len(clip_paths)

        # Build -i args
        input_args = []
        for p in clip_paths:
            input_args += ["-i", str(p)]

        # Build filter_complex:
        #   [0:v][1:v]xfade=transition=X:duration=D:offset=O[v01]
        #   [v01][2:v]xfade=transition=X:duration=D:offset=O[v012] ...
        # Audio: concat all audio streams.
        vfilter_parts = []
        aconcats = [f"[{i}:a]" for i in range(n)]
        offset = durations[0] - td
        prev_label = "[0:v]"
        for i in range(1, n):
            out_label = f"[v{i}]" if i < n - 1 else "[vout]"
            vfilter_parts.append(
                f"{prev_label}[{i}:v]xfade=transition={transition}"
                f":duration={td}:offset={offset:.4f}{out_label}"
            )
            prev_label = out_label
            if i < n - 1:
                offset += durations[i] - td

        audio_filter = "".join(aconcats) + f"concat=n={n}:v=0:a=1[aout]"
        filter_complex = ";".join(vfilter_parts) + ";" + audio_filter

        cmd = (
            ["ffmpeg", "-y"]
            + input_args
            + ["-filter_complex", filter_complex,
               "-map", "[vout]", "-map", "[aout]",
               "-c:v", "libx264", "-preset", "fast", "-crf", "18",
               "-c:a", "aac", "-b:a", "192k",
               str(out_path)]
        )
        log.debug("ffmpeg xfade cmd: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg xfade failed: {result.stderr[-800:]}")

    log.info("Stitched video saved: %s", out_path)
    return out_path


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="IRON STATIC storyboard video pipeline")
    parser.add_argument("--song", metavar="SLUG", help="Song slug (default: active song)")
    parser.add_argument("--scenes", type=int, default=3, metavar="N",
                        help="Number of scenes to generate (2–5, default 3)")
    parser.add_argument("--format", choices=list(FORMAT_ASPECT), default="landscape",
                        help="Output format (default: landscape)")
    parser.add_argument("--seed-image", metavar="PATH",
                        help="Seed image for scene 1 (relative to repo root or absolute)")
    parser.add_argument("--director-note", default="", metavar="TEXT",
                        help="Extra direction for Gemini storyboard generation")
    parser.add_argument("--transition", default="none",
                        metavar="NAME",
                        help=("xfade transition between scenes. 'none' = hard cut (default). "
                              f"Options: {', '.join(XFADE_TRANSITIONS)}"))
    parser.add_argument("--transition-duration", type=float, default=0.5,
                        metavar="SECS",
                        help="Transition overlap length in seconds (default 0.5)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate and print storyboard JSON only, no Imagen/Veo calls")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    num_scenes = max(2, min(5, args.scenes))
    fmt = args.format
    aspect = FORMAT_ASPECT[fmt]

    api_key = get_api_key()

    try:
        from google import genai
    except ImportError:
        log.error("google-genai not installed. Run: pip install google-genai")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # Load context
    song = load_active_song()
    if args.song:
        db = json.loads(SONGS_PATH.read_text())
        song = next((s for s in db.get("songs", []) if s.get("slug") == args.song), song)
    slug = song.get("slug", "brand") if song else "brand"
    log.info("Song: %s (%s)", song.get("title", slug), slug)

    brainstorm = load_brainstorm(song)
    style = load_style()

    # Resolve seed image
    seed_path: Path | None = None
    if args.seed_image:
        p = Path(args.seed_image)
        if not p.is_absolute():
            p = REPO_ROOT / p
        if p.exists():
            seed_path = p
            log.info("Seed image for scene 1: %s", seed_path)
        else:
            log.warning("Seed image not found: %s — will generate scene 1 via Imagen", args.seed_image)

    # ── Step 1: Storyboard ──
    log.info("Generating storyboard (%d scenes) via Gemini...", num_scenes)
    storyboard = generate_storyboard(
        client, song, brainstorm, style,
        num_scenes, fmt, args.director_note,
        seed_image_name=seed_path.name if seed_path else "",
    )

    print("\n=== STORYBOARD ===")
    print(f"Title: {storyboard.get('title', '')}")
    print(f"Arc:   {storyboard.get('arc', '')}")
    for s in storyboard.get("scenes", []):
        print(f"\nScene {s['id']}: {s['description']}")
        print(f"  IMAGE:     {s['image_prompt'][:120]}...")
        print(f"  ANIMATION: {s['animation_prompt'][:120]}...")
    print()

    if args.dry_run:
        out = SOCIAL_OUT / f"{slug}_storyboard.json"
        SOCIAL_OUT.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(storyboard, indent=2))
        log.info("Dry run — storyboard saved to %s", out)
        sys.exit(0)

    # ── Steps 2+3: Imagen keyframe → Veo clip per scene ──
    clip_paths: list[Path] = []
    scene_results = []

    for scene in storyboard.get("scenes", []):
        scene_id = scene["id"]
        result = {"scene": scene_id, "description": scene["description"]}

        # Keyframe
        img_path: Path | None = None
        if scene_id == 1 and seed_path:
            img_path = seed_path
            result["image"] = str(seed_path.relative_to(REPO_ROOT))
            log.info("Scene 1 using seed image: %s", img_path)
        else:
            try:
                img_path = generate_keyframe(client, scene, slug, aspect)
                result["image"] = str(img_path.relative_to(REPO_ROOT))
            except Exception as exc:
                log.error("Imagen failed for scene %d: %s", scene_id, exc)
                result["error"] = f"Imagen: {exc}"
                scene_results.append(result)
                continue

        # Veo clip
        try:
            clip = animate_scene(client, scene, img_path, slug, aspect, api_key)
            clip_paths.append(clip)
            result["video"] = str(clip.relative_to(REPO_ROOT))
        except Exception as exc:
            log.error("Veo failed for scene %d: %s", scene_id, exc)
            result["error"] = f"Veo: {exc}"
            scene_results.append(result)
            continue

        scene_results.append(result)

    # ── Step 4: ffmpeg stitch ──
    transition = args.transition
    if transition != "none" and transition not in XFADE_TRANSITIONS:
        log.warning("Unknown transition '%s' — falling back to 'none'", transition)
        transition = "none"
    final_path: Path | None = None
    if len(clip_paths) >= 2:
        try:
            final_path = concat_clips(
                clip_paths, slug, fmt,
                transition=transition,
                transition_duration=args.transition_duration,
            )
        except Exception as exc:
            log.error("Concat failed: %s", exc)
    elif len(clip_paths) == 1:
        final_path = clip_paths[0]
        log.info("Only one clip — using it as final: %s", final_path)

    print("\n=== RESULT ===")
    for r in scene_results:
        status = "✓" if "video" in r else "✗"
        print(f"  {status} Scene {r['scene']}: {r.get('video', r.get('error', 'skipped'))}")

    if final_path:
        tx_label = f"{transition} ({args.transition_duration}s)" if transition != "none" else "hard cut"
        print(f"\nFinal video: {final_path}")
        print(f"Duration:    ~{len(clip_paths) * 8}s ({len(clip_paths)} scenes × 8s)")
        print(f"Transition:  {tx_label}")
    else:
        print("\nNo final video produced — check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
