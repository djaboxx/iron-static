#!/usr/bin/env python3
"""
gemini_forge.py — Audio generation spec + optional Lyria generation for IRON STATIC.

Reads the active song's brainstorm, reference digest, and key/scale/BPM context,
then calls Gemini to produce a structured audio generation spec for a named element
(e.g. "kick loop", "bass texture", "corroded pad atmosphere").

The spec is always written to:
    audio/generated/specs/[song-slug]_[target-slug]_[date].md

If --generate is passed and GOOGLE_CLOUD_PROJECT is set, the script also attempts
to call the Lyria API and writes audio output to:
    audio/generated/[song-slug]_[target-slug]_[date].wav

Usage:
    python scripts/gemini_forge.py --target "kick loop"
    python scripts/gemini_forge.py --target "bass texture" --context "corroded, sub-heavy"
    python scripts/gemini_forge.py --target "pad atmosphere" --generate
    python scripts/gemini_forge.py --target "snare transient" --model pro
    python scripts/gemini_forge.py --target "industrial texture" --no-song-context
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import date
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
SONGS_DB = REPO_ROOT / "database" / "songs.json"
BRAINSTORMS_DIR = REPO_ROOT / "knowledge" / "brainstorms"
REFERENCES_DIR = REPO_ROOT / "knowledge" / "references"
SPECS_DIR = REPO_ROOT / "audio" / "generated" / "specs"
AUDIO_OUT_DIR = REPO_ROOT / "audio" / "generated"

IRON_STATIC_CONTEXT = """\
You are the machine half of IRON STATIC, a two-person electronic metal duo.
IRON STATIC's aesthetic: heavy, weird, electronic, intentional.
Core influences: Nine Inch Nails (industrial texture), Lamb of God (groove-metal weight),
One Day as a Lion (stripped two-member urgency), Modeselector (Berlin electronic bass pressure),
Run The Jewels (fast, political, punchy), Dr. Teeth and the Electric Mayhem (chaotic joyful weirdness).

The hardware rig:
- Elektron Digitakt MK1 — drum machine, sampler, MIDI sequencer hub
- Sequential Rev2 — 16-voice polyphonic analog (bi-timbral, Curtis filter)
- Sequential Take 5 — compact 5-voice analog poly
- Moog Subharmonicon — semi-modular polyrhythmic drone machine
- Moog DFAM — analog percussion synth (8-step sequencer, Moog ladder filter)
- Arturia Minibrute 2S — patchable mono synth + step sequencer
- Arturia Pigments — software poly (Wavetable + Analog + Sample + Harmonic engines)

Noise, distortion, and feedback are compositional elements, not mistakes."""

FORGE_PROMPT_TEMPLATE = """\
{iron_static_context}

ACTIVE SONG CONTEXT:
  Slug:  {song_slug}
  Key:   {key}
  Scale: {scale}
  BPM:   {bpm}
  Concept: "{concept}"

BRAINSTORM BRIEF:
{brainstorm_block}

REFERENCE BENCHMARKS:
{references_block}

TARGET ELEMENT: "{target}"{extra_context_block}

Your task: produce a complete audio generation spec for this element. \
Follow the exact structure below — do not add extra sections, do not omit any.

---

## GENERATION PROMPT

A single prompt string optimized for AI music generators (Suno, Udio, Google Lyria). \
Include: tempo indication, key/mode adjectives, texture descriptors, instrumentation cues, \
energy character, and relevant style references from IRON STATIC's influence list. \
Be specific and concrete. Maximum 200 words. Write it as one paragraph.

## TECHNICAL PARAMETERS

- BPM: {bpm}
- Key centre: (as relevant for this element)
- Suggested duration: Keep SHORT — maximum 30 seconds. This audio is designed to be chopped into pads. (e.g. "8 bars", "30 seconds", "4-bar loop")
- Time signature: (derive from song context and brainstorm)
- Frequency focus: (e.g. "sub/low-mid dominant", "high-mid attack transient", etc.)
- Stereo field: (mono center / wide / left-right alternating / etc.)

## HARDWARE PARALLEL

Which instrument(s) in the IRON STATIC rig would produce this element natively? \
Name the instrument and describe the key patch settings (envelope, filter, oscillator choices). \
This is the fallback if AI-generated audio is rejected or unavailable.

## INTEGRATION NOTES

How does this element relate to other parts of the song? \
What frequency ranges should it stay out of? \
Where in the arrangement does it appear (intro / build / drop / breakdown / climax / outro)? \
Reference the brainstorm structure if one exists.

## IRON STATIC FIT

Rate how well this element fits the current song direction: HIGH / MEDIUM / LOW. \
One sentence explaining why.

---"""


def load_active_song() -> dict | None:
    if not SONGS_DB.exists():
        return None
    with SONGS_DB.open() as f:
        songs = json.load(f)
    for song in songs.get("songs", []):
        if song.get("status") == "active":
            return song
    return None


def load_brainstorm(song: dict) -> str:
    brainstorm_path = song.get("brainstorm_path")
    if brainstorm_path:
        p = REPO_ROOT / brainstorm_path
        if p.exists():
            return p.read_text()
        log.warning("Brainstorm file not found: %s", p)
    # Fall back to most recent file in brainstorms dir
    files = sorted(BRAINSTORMS_DIR.glob("*.md"), reverse=True)
    if files:
        log.info("Using most recent brainstorm: %s", files[0].name)
        return files[0].read_text()
    return "(no brainstorm available)"


def load_latest_reference_digest() -> str:
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")
    files = sorted(
        (f for f in REFERENCES_DIR.glob("*.md") if pattern.match(f.name)),
        reverse=True,
    )
    if files:
        log.info("Using reference digest: %s", files[0].name)
        return files[0].read_text()
    return "(no reference digest available)"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text


def build_prompt(
    song: dict | None,
    target: str,
    extra_context: str | None,
) -> str:
    if song:
        song_slug = song.get("slug", "unknown")
        key = song.get("key", "unknown")
        scale = song.get("scale", "unknown")
        bpm = song.get("bpm", "unknown")
        concept = song.get("concept") or song.get("title", "untitled")
        brainstorm_block = load_brainstorm(song)
    else:
        song_slug = "unknown"
        key = scale = concept = "unknown"
        bpm = "unknown"
        brainstorm_block = "(running without song context)"

    references_block = load_latest_reference_digest()
    extra_context_block = f"\nAdditional context: {extra_context}" if extra_context else ""

    return FORGE_PROMPT_TEMPLATE.format(
        iron_static_context=IRON_STATIC_CONTEXT,
        song_slug=song_slug,
        key=key,
        scale=scale,
        bpm=bpm,
        concept=concept,
        brainstorm_block=brainstorm_block,
        references_block=references_block,
        target=target,
        extra_context_block=extra_context_block,
    )


def call_gemini(prompt: str, model_tier: str) -> str:
    try:
        from google import genai
    except ImportError:
        log.error("google-genai not installed. Run: pip install google-genai>=1.0.0")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        log.error("Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")
        sys.exit(1)

    model_map = {
        "fast": os.environ.get("GEMINI_MODEL_FAST", "gemini-2.5-flash"),
        "pro": os.environ.get("GEMINI_MODEL_PRO", "gemini-2.5-pro"),
    }
    model_name = model_map.get(model_tier, model_map["fast"])
    log.info("Calling Gemini model=%s ...", model_name)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=model_name, contents=prompt)
    return response.text


def _build_lyria_prompt(spec_text: str) -> str:
    """
    Build a minimal, Lyria-safe prompt from the spec's TECHNICAL PARAMETERS section.

    The GENERATION PROMPT section always contains IRON STATIC aesthetic prose
    ("corrosive," "dread," "inevitable," etc.) that trips Lyria's content filter.
    This function builds a clean, genre/production-vocabulary prompt instead.
    """
    params: dict = {}
    tp_match = re.search(r"## TECHNICAL PARAMETERS\s*\n+(.*?)(?=##|\Z)", spec_text, re.DOTALL)
    if tp_match:
        block = tp_match.group(1)
        for line in block.splitlines():
            line = line.strip("- ").strip()
            if ":" not in line:
                continue
            k, _, v = line.partition(":")
            params[k.strip().lower()] = v.strip()

    bpm = params.get("bpm", "120")
    key = params.get("key centre", params.get("key center", "C minor"))
    duration = params.get("suggested duration", "30 seconds")
    freq_focus = params.get("frequency focus", "full spectrum")
    time_sig = params.get("time signature", "4/4")

    # Strip parens/extra commentary from duration
    duration = re.sub(r"\(.*?\)", "", duration).strip()

    prompt = (
        f"Instrumental electronic music, short loop. "
        f"Tempo: {bpm} BPM. Key: {key}. Time signature: {time_sig}. "
        f"Duration: {duration}. Maximum 30 seconds. "
        f"Genre: industrial ambient, dark electronic, noise music. "
        f"Texture: layered synthesizer drones, metallic percussion, sub-bass, "
        f"granular synthesis, heavy distortion, evolving atmospheric pads. "
        f"Frequency focus: {freq_focus}. "
        f"Stereo field: wide. No vocals."
    )
    return prompt


def generate_lyria(spec_text: str, target: str, song_slug: str, out_path: Path, model: str) -> bool:
    """
    Generate audio via Lyria 3 through the Gemini API.

    Uses the same GEMINI_API_KEY as all other Gemini calls — no Vertex AI required.
    Models:
      lyria-3-clip-preview — 30-second loops/samples, MP3 output (default)
      lyria-3-pro-preview  — full-length songs, MP3 or WAV output

    Returns True on success, False on failure.
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        log.error("google-genai not installed. Run: pip install google-genai>=1.0.0")
        return False

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        log.error("Set GEMINI_API_KEY or GOOGLE_API_KEY to use Lyria generation.")
        return False

    # Extract the GENERATION PROMPT section from the spec
    # Lyria's content filter blocks aesthetic/emotional language (even in music context).
    # Build a clean, technical-only prompt from the TECHNICAL PARAMETERS section instead
    # of using the GENERATION PROMPT which always contains IRON STATIC aesthetic prose.
    generation_prompt = _build_lyria_prompt(spec_text)
    if not generation_prompt:
        log.error("Could not extract TECHNICAL PARAMETERS from spec. Cannot call Lyria.")
        return False
    log.info("Built Lyria-safe prompt (%d chars).", len(generation_prompt))

    lyria_model = model if model.startswith("lyria-") else "lyria-3-clip-preview"
    log.info("Calling %s via Gemini API...", lyria_model)

    try:
        client = genai.Client(api_key=api_key)

        # Both Lyria models return MP3 audio — extension corrected from magic bytes later
        out_path = out_path.with_suffix(".mp3")
        response = client.models.generate_content(
            model=lyria_model,
            contents=generation_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
            ),
        )

        # Lyria returns via candidates[0].content.parts; .parts is not a top-level attr
        audio_data = None
        parts = []

        # Check for content filter block before inspecting parts
        pf = getattr(response, "prompt_feedback", None)
        if pf and getattr(pf, "block_reason", None):
            log.error("Lyria blocked prompt: block_reason=%s — prompt language triggered safety filter.",
                      pf.block_reason)
            return False

        if hasattr(response, "parts") and response.parts:
            parts = response.parts
        elif hasattr(response, "candidates") and response.candidates:
            content = getattr(response.candidates[0], "content", None)
            if content and hasattr(content, "parts"):
                parts = content.parts
        # Debug: log structure if no audio found
        if not parts:
            log.warning("Response parts empty. candidates=%s text=%s",
                        getattr(response, "candidates", None),
                        getattr(response, "text", None))
        for part in parts:
            if getattr(part, "inline_data", None) is not None:
                audio_data = part.inline_data.data
            elif getattr(part, "text", None):
                log.info("Lyria returned text: %s", part.text[:200])

        if not audio_data:
            log.error("Lyria response contained no audio data.")
            # Dump response repr for diagnosis
            log.warning("Response repr: %s", repr(response)[:1000])
            return False

        # Detect actual format from magic bytes and correct extension if needed
        if audio_data[:4] == b'RIFF':
            out_path = out_path.with_suffix(".wav")
        else:
            out_path = out_path.with_suffix(".mp3")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(audio_data)
        log.info("Audio written to %s (%d bytes).", out_path, len(audio_data))
        return True

    except Exception as exc:
        log.error("Lyria generation failed: %s", exc)
        return False


def write_spec(
    spec_text: str,
    target: str,
    song_slug: str,
    today: str,
) -> Path:
    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    target_slug = slugify(target)
    out_path = SPECS_DIR / f"{song_slug}_{target_slug}_{today}.md"

    header = (
        f"# Audio Generation Spec: {target}\n\n"
        f"**Song**: {song_slug}  \n"
        f"**Date**: {today}  \n\n"
        "---\n\n"
    )
    out_path.write_text(header + spec_text)
    return out_path


def push_to_gcs(audio_path: Path, song_slug: str, skip: bool = False) -> None:
    """Push a generated audio file to GCS using gcs_sync.py.

    If GCS_BUCKET is not set or --no-gcs-push was passed, log the manual
    command instead so the user knows exactly what to run.
    """
    if skip:
        log.info(
            "GCS push skipped (--no-gcs-push). To upload manually:\n"
            "  python scripts/gcs_sync.py push %s --tag %s",
            audio_path,
            song_slug,
        )
        return

    if not os.environ.get("GCS_BUCKET"):
        log.warning(
            "GCS_BUCKET env var not set — skipping auto-push. Upload manually:\n"
            "  python scripts/gcs_sync.py push %s --tag %s",
            audio_path,
            song_slug,
        )
        return

    import subprocess

    gcs_sync = Path(__file__).parent / "gcs_sync.py"
    cmd = [sys.executable, str(gcs_sync), "push", str(audio_path), "--tag", song_slug]
    log.info("Pushing to GCS: %s", " ".join(cmd))
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        log.error(
            "GCS push failed (exit %d). Upload manually:\n"
            "  python scripts/gcs_sync.py push %s --tag %s",
            result.returncode,
            audio_path,
            song_slug,
        )
    else:
        log.info("GCS push succeeded — update the manifest in git:")
        log.info("  git add database/gcs_manifest.json && git commit -m 'chore: upload %s to GCS'", audio_path.name)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate an IRON STATIC audio spec (and optionally audio) via Gemini."
    )
    parser.add_argument(
        "--target",
        required=True,
        metavar="ELEMENT",
        help=(
            'The sonic element to generate a spec for. '
            'Examples: "kick loop", "bass texture", "corroded pad", "industrial hit".'
        ),
    )
    parser.add_argument(
        "--context",
        default=None,
        metavar="TEXT",
        help="Optional extra context to append to the prompt (mood words, constraints, etc.).",
    )
    parser.add_argument(
        "--model",
        choices=["fast", "pro"],
        default="fast",
        help="Gemini model tier: 'fast' (gemini-2.5-flash) or 'pro' (gemini-2.5-pro). Default: fast.",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help=(
            "Generate audio via Lyria 3 through the Gemini API (same GEMINI_API_KEY). "
            "Writes an .mp3 (or .wav for --lyria-model pro) to audio/generated/."
        ),
    )
    parser.add_argument(
        "--lyria-model",
        choices=["clip", "pro"],
        default="clip",
        help=(
            "Lyria 3 model to use for --generate: "
            "'clip' (lyria-3-clip-preview, 30-second loop, MP3) or "
            "'pro' (lyria-3-pro-preview, full-length, MP3 or WAV). Default: clip."
        ),
    )
    parser.add_argument(
        "--no-gcs-push",
        action="store_true",
        help=(
            "Skip automatic GCS upload after --generate. "
            "Use this if GCS credentials are not available locally. "
            "The gcs_sync.py push command will be printed instead."
        ),
    )
    parser.add_argument(
        "--no-song-context",
        action="store_true",
        help="Skip loading active song context. Produces a generic IRON STATIC spec.",
    )
    parser.add_argument(
        "--date",
        default=None,
        metavar="YYYY-MM-DD",
        help="Override output date (default: today).",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Print the spec as text (default) or as a JSON envelope.",
    )
    args = parser.parse_args()

    today = args.date or str(date.today())

    active_song = None if args.no_song_context else load_active_song()
    if active_song:
        log.info(
            "Active song: %s (key=%s, scale=%s, bpm=%s)",
            active_song.get("slug"),
            active_song.get("key"),
            active_song.get("scale"),
            active_song.get("bpm"),
        )
    else:
        log.info("No active song context.")

    song_slug = active_song.get("slug", "iron-static") if active_song else "iron-static"

    prompt = build_prompt(active_song, args.target, args.context)
    spec_text = call_gemini(prompt, args.model)

    spec_path = write_spec(spec_text, args.target, song_slug, today)
    log.info("Spec written to: %s", spec_path)

    audio_path = None
    if args.generate:
        lyria_model_map = {
            "clip": "lyria-3-clip-preview",
            "pro": "lyria-3-pro-preview",
        }
        lyria_model_name = lyria_model_map[args.lyria_model]
        target_slug = slugify(args.target)
        suffix = ".mp3"  # Lyria always returns MP3 regardless of model variant
        audio_path = AUDIO_OUT_DIR / f"{song_slug}_{target_slug}_{today}{suffix}"
        success = generate_lyria(spec_text, args.target, song_slug, audio_path, lyria_model_name)
        if not success:
            audio_path = None
            log.info(
                "Lyria generation failed — spec file is your deliverable. "
                "Use the GENERATION PROMPT section with an audio generator of your choice."
            )
        else:
            push_to_gcs(audio_path, song_slug, skip=args.no_gcs_push)

    if args.output == "json":
        result = {
            "song_slug": song_slug,
            "target": args.target,
            "date": today,
            "spec_path": str(spec_path),
            "audio_path": str(audio_path) if audio_path else None,
            "spec": spec_text,
        }
        print(json.dumps(result, indent=2))
    else:
        print(spec_text)
        print(f"\n---\nSpec saved: {spec_path}", file=sys.stderr)
        if audio_path:
            print(f"Audio saved: {audio_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
