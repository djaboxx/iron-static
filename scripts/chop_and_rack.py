#!/usr/bin/env python3
"""
chop_and_rack.py — Gemini-guided creative audio chopper + Ableton Drum Rack builder.

Sends an audio file to Gemini's multimodal API to get CREATIVE chop point suggestions
(not transient-based — Gemini picks musically meaningful moments). Slices the audio at
those points, saves the slices to audio/generated/slices/, then builds a .adg Drum Rack
preset file with each slice loaded into a Simpler pad.

Pipeline:
  1. Upload audio to Gemini Files API
  2. Ask Gemini for N creative chop points (timestamps in seconds) with reasoning
  3. Parse timestamps → slice audio with soundfile
  4. Save slices to audio/generated/slices/[song-slug]_[source-slug]_[date]/
  5. Build .adg DrumGroupDevice with N pads (Simpler per pad, absolute FileRef)
  6. Save .adg to ableton/racks/[song-slug]_[source-slug]_[date].adg
  7. Optionally push slices to GCS

Usage:
    python scripts/chop_and_rack.py --file audio/generated/rust-protocol_kick-loop_2026-04-24.mp3
    python scripts/chop_and_rack.py --file loop.wav --slices 8 --context "focus on rhythmic gaps and textural ruptures"
    python scripts/chop_and_rack.py --file loop.wav --slices 16 --rack-name "Rust Chops" --push-gcs
"""

import argparse
import gzip
import json
import logging
import os
import re
import sys
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr)
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
SONGS_DB = REPO_ROOT / "database" / "songs.json"
SLICES_DIR = REPO_ROOT / "audio" / "generated" / "slices"
RACKS_DIR = REPO_ROOT / "ableton" / "racks"

# Chromatic sequential pad layout starting at C1 (note 36)
# Matches Live's default behavior when creating a Drum Rack from samples
PAD_NOTES = list(range(36, 36 + 128))  # 36..163, chromatic ascending


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# ---------------------------------------------------------------------------
# Song context
# ---------------------------------------------------------------------------

def load_active_song() -> dict | None:
    if not SONGS_DB.exists():
        return None
    songs = json.loads(SONGS_DB.read_text())
    for song in songs.get("songs", []):
        if song.get("status") == "active":
            return song
    return None


# ---------------------------------------------------------------------------
# Stem separation (optional, requires demucs)
# ---------------------------------------------------------------------------

def separate_all_stems(audio_path: Path) -> "dict[str, Path]":
    """
    Run Demucs htdemucs_ft full 4-stem separation on audio_path.

    Returns an ordered dict: {"other": Path, "drums": Path, "bass": Path, "vocals": Path}
    ordered by IRON STATIC usefulness — other (texture) first for pad layout priority.
    """
    try:
        import demucs.separate  # noqa: F401
    except ImportError:
        log.error("demucs not installed. Run: pip install demucs>=4.0.0")
        sys.exit(1)

    stems_out = REPO_ROOT / "audio" / "generated" / "stems"
    stems_out.mkdir(parents=True, exist_ok=True)

    log.info("Running Demucs htdemucs_ft (all stems) on %s — this may take a minute...",
             audio_path.name)

    import subprocess
    result = subprocess.run(
        [
            sys.executable, "-m", "demucs",
            "-n", "htdemucs_ft",
            "-o", str(stems_out),
            str(audio_path.resolve()),
        ],
    )
    if result.returncode != 0:
        log.error("Demucs failed (exit %d).", result.returncode)
        sys.exit(1)

    # Demucs output: stems_out/htdemucs_ft/<source-stem>/{drums,bass,vocals,other}.wav
    demucs_dir = stems_out / "htdemucs_ft" / audio_path.stem

    # IRON STATIC pad layout order: drums first (bottom of rack), then bass, vocals, other
    stem_order = ["drums", "bass", "vocals", "other"]
    stem_map: dict[str, Path] = {}
    for name in stem_order:
        p = demucs_dir / f"{name}.wav"
        if not p.exists():
            log.error("Expected stem file not found: %s", p)
            if demucs_dir.exists():
                log.error("Demucs output dir contains: %s", list(demucs_dir.iterdir()))
            sys.exit(1)
        stem_map[name] = p
        log.info("  stem '%s': %s", name, p)

    return stem_map


# ---------------------------------------------------------------------------
# Gemini: creative chop points
# ---------------------------------------------------------------------------

CHOP_PROMPT_TEMPLATE = """\
You are the machine half of IRON STATIC, an electronic metal duo. \
IRON STATIC makes heavy, weird, electronic, intentional music in the aesthetic of \
Nine Inch Nails, Lamb of God, Modeselector, and Run the Jewels.

You are listening to an audio file that will be chopped into sample slices \
and loaded into an Ableton Drum Rack. The goal is NOT transient-based chopping. \
The goal is CREATIVE, MUSICAL chopping — picking moments that will produce \
interesting, usable fragments: textural ruptures, density changes, spectral surprises, \
rhythmic gaps, tonal anomalies, or moments of unexpected contrast.

Active song context: {song_context}
Extra instructions: {extra_context}

Please suggest exactly {n_slices} chop regions for this audio.

Each chop has an INDEPENDENT start AND end. They need not be contiguous — gaps and
overlaps between chops are allowed and often musically interesting. Choose the end
point that captures the most interesting tail of each moment, not just where the next
chop begins.

Respond with ONLY a JSON object in this exact format — no markdown, no preamble:
{{
  "duration_seconds": <estimated total duration as a float>,
  "chop_strategy": "<one sentence describing your creative approach>",
  "chops": [
    {{"start": <float seconds>, "end": <float seconds>, "reason": "<brief description>"}},
    ...
  ]
}}

The first chop should almost always start at 0.0.
Distribute all {n_slices} chops across the file in musically interesting ways.
All start times must be in ascending order. Starts and ends must be within the file duration.
Ends must be greater than their corresponding start.
"""


def ask_gemini_for_chops(audio_path: Path, n_slices: int, song: dict | None,
                          extra_context: str, model: str) -> dict:
    """Upload audio to Gemini Files API and ask for creative chop points."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        log.error("google-genai not installed. Run: pip install google-genai>=1.0.0")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        log.error("Set GEMINI_API_KEY to use Gemini chop analysis.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    song_context = "none"
    if song:
        song_context = (
            f"key={song.get('key','?')}, scale={song.get('scale','?')}, "
            f"bpm={song.get('bpm','?')}, title={song.get('title','?')}"
        )

    prompt = CHOP_PROMPT_TEMPLATE.format(
        song_context=song_context,
        extra_context=extra_context or "none — use your best creative judgment",
        n_slices=n_slices,
    )

    log.info("Uploading %s to Gemini Files API...", audio_path.name)
    mime_map = {".wav": "audio/wav", ".mp3": "audio/mp3", ".aif": "audio/aiff",
                ".aiff": "audio/aiff", ".flac": "audio/flac", ".ogg": "audio/ogg"}
    mime = mime_map.get(audio_path.suffix.lower(), "audio/wav")

    uploaded = client.files.upload(file=str(audio_path), config={"mime_type": mime})
    log.info("Uploaded as %s. Querying Gemini model=%s...", uploaded.name, model)

    try:
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Content(parts=[
                    types.Part(text=prompt),
                    types.Part(file_data=types.FileData(
                        file_uri=uploaded.uri,
                        mime_type=mime,
                    )),
                ])
            ],
        )
    finally:
        try:
            client.files.delete(name=uploaded.name)
            log.info("Deleted uploaded file from Gemini Files API.")
        except Exception:
            pass

    raw = response.text.strip()
    # Strip any accidental markdown fences
    raw = re.sub(r"^```[a-z]*\n?", "", raw).strip("`").strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.error("Gemini returned invalid JSON: %s\nRaw response:\n%s", exc, raw[:500])
        sys.exit(1)

    return result


# ---------------------------------------------------------------------------
# Audio slicing
# ---------------------------------------------------------------------------

def slice_audio(audio_path: Path, chop_data: dict, out_dir: Path) -> list[Path]:
    """
    Slice audio at the Gemini-suggested chop points.
    Returns list of slice file paths in pad order.
    """
    try:
        import soundfile as sf
        import numpy as np
    except ImportError:
        log.error("soundfile and numpy are required. Run: pip install soundfile numpy")
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)

    data, samplerate = sf.read(str(audio_path), always_2d=True)
    total_samples = len(data)
    total_seconds = total_samples / samplerate
    log.info("Loaded: %.2f seconds, %d samples @ %d Hz", total_seconds, total_samples, samplerate)

    chops = chop_data.get("chops", [])
    if not chops:
        log.error("No chop points returned by Gemini.")
        sys.exit(1)

    # Support both new format {start, end} and legacy format {time} (infer end from next start).
    def _start(c: dict) -> float:
        return max(0.0, min(float(c.get("start", c.get("time", 0.0))), total_seconds))
    def _end(c: dict, next_start: float) -> float:
        raw = c.get("end", next_start)
        return max(0.0, min(float(raw), total_seconds))

    chops_sorted = sorted(chops, key=_start)
    slice_paths = []
    for i, c in enumerate(chops_sorted):
        # Fallback end: start of next chop (or file end for last chop)
        next_s = _start(chops_sorted[i + 1]) if i + 1 < len(chops_sorted) else total_seconds
        start_sec = _start(c)
        end_sec = _end(c, next_s)
        if end_sec <= start_sec:
            log.warning("Slice %d has zero length (%.3f–%.3f), skipping.", i, start_sec, end_sec)
            continue

        start_sample = int(start_sec * samplerate)
        end_sample = int(end_sec * samplerate)
        chunk = data[start_sample:end_sample]
        slice_name = f"slice_{i:02d}_{start_sec:.3f}s.wav"
        slice_path = out_dir / slice_name
        sf.write(str(slice_path), chunk, samplerate)
        log.info("  Slice %02d: %.3f–%.3f s (%d samples) — %s", i, start_sec, end_sec,
                 len(chunk), c.get("reason", "")[:60])
        slice_paths.append(slice_path)

    return slice_paths


# ---------------------------------------------------------------------------
# .adg builder — template-based, using reference ADG for schema accuracy
# ---------------------------------------------------------------------------

# Path to factory-saved Drum Rack preset used as structural template.
# This ensures Live 12 can load the generated preset without schema errors.
_REFERENCE_ADG = REPO_ROOT / "ableton" / "racks" / "808 Depth Charger Kit.adg"


def _load_reference_templates() -> tuple[str, str, str]:
    """
    Load and return (header, footer, pad_template) from the reference ADG.

    header: everything from <?xml ...> up to (not including) <BranchPresets>
    footer: from </BranchPresets> to end
    pad_template: the full XML of the first DrumBranchPreset (Id="0")
    """
    if not _REFERENCE_ADG.exists():
        log.error(
            "Reference ADG not found: %s\n"
            "Save a factory Drum Rack preset to ableton/racks/ as '808 Depth Charger Kit.adg'.",
            _REFERENCE_ADG,
        )
        sys.exit(1)

    xml = gzip.open(_REFERENCE_ADG).read().decode("utf-8")

    bp_start = xml.index("<BranchPresets>")
    bp_end = xml.index("</BranchPresets>")

    header = xml[:bp_start]
    footer = xml[bp_end:]

    # Extract the first full DrumBranchPreset block
    pad_open = '<DrumBranchPreset Id="0">'
    pad_close = "</DrumBranchPreset>"
    pad_start = xml.index(pad_open)
    pad_end = xml.index(pad_close, pad_start) + len(pad_close)
    pad_template = xml[pad_start:pad_end]

    return header, footer, pad_template


def _adapt_pad(template: str, pad_idx: int, note: int, sample_path: Path,
               slice_name: str, choke_group: int = 0) -> str:
    """
    Adapt the reference DrumBranchPreset template for a new sample slice.

    Substitutions made (all via regex, preserving all other fields verbatim):
      - DrumBranchPreset/AbletonDevicePreset Id attributes → pad_idx
      - UserName (OriginalSimpler preset name) → slice_name
      - MultiSamplePart Name → slice_name (first 16 chars)
      - ReceivingNote → note
      - ChokeGroup → choke_group (0=off, 1-16=group)
      - All FileRef blocks with non-empty paths → absolute path to sample_path
      - SampleEnd, loop End values, DefaultDuration → actual frame count
      - DefaultSampleRate → actual sample rate
      - LastModDate → 0
      - BrowserContentPath → empty
    """
    try:
        import soundfile as sf
    except ImportError:
        log.error("soundfile required: pip install soundfile")
        sys.exit(1)

    info = sf.info(str(sample_path))
    frame_count = info.frames
    sample_rate = info.samplerate
    abs_path = str(sample_path.resolve())

    t = template

    # --- Pad identity ---
    t = t.replace('<DrumBranchPreset Id="0">', f'<DrumBranchPreset Id="{pad_idx}">', 1)
    t = t.replace('<AbletonDevicePreset Id="0">', f'<AbletonDevicePreset Id="{pad_idx}">', 1)

    # --- Pad name (shown in Drum Rack UI) ---
    t = re.sub(r'(<DrumBranchPreset[^>]*>\s*<Name Value=")[^"]*(")',
               r'\g<1>' + slice_name + r'\g<2>', t, count=1)

    # --- OriginalSimpler UserName (preset name label) ---
    t = re.sub(r'<UserName Value="[^"]*" />', f'<UserName Value="{slice_name}" />', t, count=1)

    # --- MultiSamplePart Name ---
    t = re.sub(r'<Name Value="[^"]*" />', f'<Name Value="{slice_name[:16]}" />', t, count=1)

    # --- ReceivingNote ---
    t = re.sub(r'<ReceivingNote Value="\d+" />', f'<ReceivingNote Value="{note}" />', t)

    # --- Choke group ---
    t = re.sub(r'<ChokeGroup Value="\d+" />', f'<ChokeGroup Value="{choke_group}" />', t)

    # --- FileRef blocks: replace all that have a non-empty Path ---
    def _repl_fileref(m: re.Match) -> str:
        tag_open = m.group(1)   # e.g. '<FileRef>' or '<FileRef Id="16">'
        inner = m.group(2)
        # Skip empty-path refs (e.g. LastPresetRef inside OriginalSimpler)
        if re.search(r'<Path Value="" />', inner):
            return m.group(0)
        inner = re.sub(r'<RelativePathType Value="\d+" />', '<RelativePathType Value="0" />', inner)
        inner = re.sub(r'<RelativePath Value="[^"]*" />', '<RelativePath Value="" />', inner)
        inner = re.sub(r'<Path Value="[^"]*" />', f'<Path Value="{abs_path}" />', inner)
        inner = re.sub(r'<Type Value="\d+" />', '<Type Value="1" />', inner)
        inner = re.sub(r'<LivePackName Value="[^"]*" />', '<LivePackName Value="" />', inner)
        inner = re.sub(r'<LivePackId Value="[^"]*" />', '<LivePackId Value="" />', inner)
        inner = re.sub(r'<OriginalFileSize Value="\d+" />', '<OriginalFileSize Value="0" />', inner)
        inner = re.sub(r'<OriginalCrc Value="\d+" />', '<OriginalCrc Value="0" />', inner)
        return f"{tag_open}{inner}</FileRef>"

    t = re.sub(r'(<FileRef[^>]*>)(.*?)</FileRef>', _repl_fileref, t, flags=re.DOTALL)

    # --- BrowserContentPath ---
    t = re.sub(r'<BrowserContentPath Value="[^"]*" />', '<BrowserContentPath Value="" />', t)

    # --- Sample frame count ---
    t = re.sub(r'<SampleEnd Value="\d+" />', f'<SampleEnd Value="{frame_count}" />', t)
    t = re.sub(r'<End Value="\d+" />', f'<End Value="{frame_count}" />', t)
    t = re.sub(r'<DefaultDuration Value="\d+" />', f'<DefaultDuration Value="{frame_count}" />', t)

    # --- Sample rate ---
    t = re.sub(r'<DefaultSampleRate Value="\d+" />', f'<DefaultSampleRate Value="{sample_rate}" />', t)

    # --- Clear stale timestamps ---
    t = re.sub(r'<LastModDate Value="\d+" />', '<LastModDate Value="0" />', t)

    return t


def build_adg(slice_paths: list[Path], rack_name: str, chop_data: dict) -> bytes:
    """
    Build a complete DrumGroupDevice .adg as gzip-compressed XML bytes.

    Uses the factory '808 Depth Charger Kit.adg' as a structural template so that
    Live 12 can load the preset without schema errors. Per-pad substitutions replace
    the file path, sample end frame, receiving note, and name fields while keeping
    all envelope/filter/modulation parameters verbatim from the reference.
    """
    strategy = chop_data.get("chop_strategy", "creative chops")

    header, footer, pad_template = _load_reference_templates()

    # Adapt the DrumGroupDevice header: update rack name and annotation only.
    header = re.sub(r'<UserName Value="[^"]*" />', f'<UserName Value="{rack_name}" />',
                    header, count=1)
    header = re.sub(
        r'<Annotation Value="[^"]*" />',
        f'<Annotation Value="Generated by IRON STATIC chop_and_rack.py. Strategy: {strategy}" />',
        header, count=1,
    )

    # Choke groups by stem: drums=1, bass=2, vocals=3, other=4, non-stem=0
    _STEM_DIRS = {"drums", "bass", "vocals", "other"}
    _STEM_CHOKE = {"drums": 1, "bass": 2, "vocals": 3, "other": 4}

    pads = []
    for i, sp in enumerate(slice_paths[:128]):
        pad_note = PAD_NOTES[i] if i < len(PAD_NOTES) else 36 + i
        stem_dir = sp.parent.name if sp.parent.name in _STEM_DIRS else None
        display_name = f"{stem_dir}_{sp.stem}" if stem_dir else sp.stem
        choke_group = _STEM_CHOKE.get(stem_dir, 0) if stem_dir else 0
        pads.append(_adapt_pad(pad_template, i, pad_note, sp, display_name, choke_group))

    xml = header + "<BranchPresets>\n" + "\n".join(pads) + "\n" + footer
    return gzip.compress(xml.encode("utf-8"), compresslevel=6)


# ---------------------------------------------------------------------------
# GCS push helper
# ---------------------------------------------------------------------------

def push_slices_to_gcs(slice_dir: Path, song_slug: str) -> None:
    """Push all slices in slice_dir to GCS using gcs_sync.py."""
    import subprocess

    bucket = os.environ.get("GCS_BUCKET")
    if not bucket:
        log.warning(
            "GCS_BUCKET not set — skipping GCS push. Upload slices manually:\n"
            "  python scripts/gcs_sync.py push %s --tag %s",
            slice_dir,
            song_slug,
        )
        return

    gcs_sync = Path(__file__).parent / "gcs_sync.py"
    cmd = [sys.executable, str(gcs_sync), "push", str(slice_dir), "--tag", song_slug]
    log.info("Pushing slices to GCS: %s", " ".join(cmd))
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        log.error(
            "GCS push failed (exit %d). Upload manually:\n"
            "  python scripts/gcs_sync.py push %s --tag %s",
            result.returncode,
            slice_dir,
            song_slug,
        )
    else:
        log.info("GCS push succeeded. Commit the manifest:\n"
                 "  git add database/gcs_manifest.json && git commit -m 'chore: upload slices to GCS'")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Gemini-guided creative audio chopper + Ableton Drum Rack builder.\n"
            "Asks Gemini for musically interesting chop points (not transient-based),\n"
            "slices the audio, and builds a .adg Drum Rack preset."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--file",
        required=True,
        metavar="PATH",
        help="Audio file to chop (WAV, MP3, AIFF, FLAC supported).",
    )
    parser.add_argument(
        "--slices",
        type=int,
        default=8,
        metavar="N",
        help="Number of slices / pads to generate (2–16, default 8).",
    )
    parser.add_argument(
        "--context",
        default="",
        metavar="TEXT",
        help='Extra creative instructions for chop point selection (e.g. "focus on textural ruptures").',
    )
    parser.add_argument(
        "--rack-name",
        default=None,
        metavar="NAME",
        help="Name for the Drum Rack preset (default: derived from source filename).",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash",
        metavar="MODEL",
        help="Gemini model to use for chop analysis (default: gemini-2.5-flash).",
    )
    parser.add_argument(
        "--date",
        default=None,
        metavar="YYYY-MM-DD",
        help="Override output date (default: today).",
    )
    parser.add_argument(
        "--push-gcs",
        action="store_true",
        help="Push slices to GCS via gcs_sync.py after chopping.",
    )
    parser.add_argument(
        "--stems",
        action="store_true",
        help=(
            "Run Demucs full 4-stem separation (drums/bass/vocals/other). "
            "Chop points are determined from the original file; the same cuts are "
            "applied to every stem. All slices are packed into one Drum Rack in "
            "stem order: drums, bass, vocals, other. "
            "Requires: pip install demucs>=4.0.0"
        ),
    )
    parser.add_argument(
        "--stem-select",
        metavar="STEM",
        nargs="+",
        choices=["drums", "bass", "vocals", "other"],
        help=(
            "When using --stems, only include these stem(s) in the rack. "
            "E.g. --stem-select other  →  pad/texture rack, no drums/bass. "
            "Multiple: --stem-select other vocals. Default: all 4 stems."
        ),
    )
    parser.add_argument(
        "--load-track",
        metavar="TRACK",
        help=(
            "After building the .adg, stage it to the Live User Library and load it onto "
            "this track name (e.g. 'Corroded Pads'). Requires Ableton to be running with "
            "the IronStatic Remote Script loaded."
        ),
    )
    parser.add_argument(
        "--no-song-context",
        action="store_true",
        help="Skip loading active song context.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print chop points from Gemini but do not write any files.",
    )
    args = parser.parse_args()

    n = max(2, min(16, args.slices))
    today = args.date or str(date.today())

    audio_path = Path(args.file)
    if not audio_path.exists():
        log.error("File not found: %s", audio_path)
        sys.exit(1)

    song = None if args.no_song_context else load_active_song()
    if song:
        log.info("Active song: %s (%s %s, %s BPM)", song.get("slug"), song.get("key"),
                 song.get("scale"), song.get("bpm"))

    song_slug = song.get("slug", "iron-static") if song else "iron-static"

    source_slug = slugify(audio_path.stem)
    rack_name = args.rack_name or f"{source_slug} chops"

    # Resolve slice_dir early so we can check for existing chop metadata.
    slice_dir = SLICES_DIR / f"{song_slug}_{source_slug}_{today}"
    meta_path = slice_dir / "chop_metadata.json"

    # Step 1: Ask Gemini for chop points — ALWAYS from the original unseparated file.
    # The full mix has more spectral information than any individual stem, so Gemini
    # finds better moments here. The same timestamps are then applied to every stem.
    #
    # Idempotency: if valid chop metadata already exists for this slug+date, reuse it
    # instead of calling Gemini again. This prevents a --stems re-run from overwriting
    # good chop times with a bad Gemini response.
    chop_data = None
    if meta_path.exists() and not args.dry_run:
        try:
            existing = json.loads(meta_path.read_text())
            # Support both {start} (new) and {time} (legacy) formats.
            existing_starts = [
                float(c.get("start", c.get("time", 0))) for c in existing.get("chops", [])
            ]
            span = (existing_starts[-1] - existing_starts[0]) if len(existing_starts) > 1 else 0
            if span >= 1.0:
                log.info("Reusing existing chop metadata (span=%.1fs): %s", span, meta_path)
                chop_data = existing
            else:
                log.warning("Existing chop metadata span=%.3fs is too small; re-asking Gemini.", span)
        except Exception as exc:
            log.warning("Could not load existing chop metadata (%s); re-asking Gemini.", exc)

    if chop_data is None:
        chop_data = ask_gemini_for_chops(audio_path, n, song, args.context, args.model)

        # Validate: if Gemini returned implausibly tiny chop times, abort immediately.
        chop_starts = [
            float(c.get("start", c.get("time", 0))) for c in chop_data.get("chops", [])
        ]
        span = (chop_starts[-1] - chop_starts[0]) if len(chop_starts) > 1 else 0
        gemini_duration = chop_data.get("duration_seconds", 0)
        min_expected = max(1.0, 0.1 * gemini_duration)
        if span < min_expected:
            log.error(
                "Gemini returned bad chop times (span=%.3fs, estimated_duration=%.1fs). "
                "This is a hallucinated response. Re-run to retry with a fresh Gemini call.",
                span, gemini_duration,
            )
            sys.exit(1)

        # Validate: check that chops aren't mostly out-of-bounds relative to actual file duration.
        try:
            import soundfile as _sf
            _info = _sf.info(str(audio_path))
            actual_duration = _info.frames / _info.samplerate
            out_of_bounds = sum(1 for s in chop_starts if s > actual_duration)
            if out_of_bounds > len(chop_starts) // 2:
                log.error(
                    "%d/%d chop starts are beyond actual file duration (%.1fs). "
                    "Gemini estimated %.1fs — hallucinated duration. Re-run to retry.",
                    out_of_bounds, len(chop_starts), actual_duration, gemini_duration,
                )
                sys.exit(1)
            elif out_of_bounds > 0:
                log.warning(
                    "%d/%d chop starts exceed actual file duration (%.1fs) and will be skipped.",
                    out_of_bounds, len(chop_starts), actual_duration,
                )
        except Exception as _e:
            log.debug("Could not pre-validate chop bounds: %s", _e)

    log.info("Chop strategy: %s", chop_data.get("chop_strategy", "?"))
    log.info("Estimated duration: %.2f s", chop_data.get("duration_seconds", 0))
    for i, c in enumerate(chop_data.get("chops", [])):
        start = c.get("start", c.get("time", "?"))
        end = c.get("end", "?")
        log.info("  Chop %02d: %.3f–%s s — %s", i, start, end, c.get("reason", "")[:80])

    if args.dry_run:
        print(json.dumps(chop_data, indent=2))
        return

    # Step 2: Slice — either stem-separated (all 4 stems, same chop points) or direct
    if args.stems:
        # Separate all 4 stems; apply identical chop timestamps to each.
        stem_map = separate_all_stems(audio_path)
        if args.stem_select:
            selected = [s for s in ["drums", "bass", "vocals", "other"] if s in args.stem_select]
            stem_map = {k: v for k, v in stem_map.items() if k in selected}
            log.info("stem-select: building rack from %s only", selected)
        slice_paths = []
        for stem_name, stem_path in stem_map.items():
            log.info("Slicing '%s' stem...", stem_name)
            stem_slices = slice_audio(stem_path, chop_data, slice_dir / stem_name)
            slice_paths.extend(stem_slices)
        log.info("Total slices across %d stems: %d", len(stem_map), len(slice_paths))
    else:
        slice_paths = slice_audio(audio_path, chop_data, slice_dir)

    if not slice_paths:
        log.error("No slices produced.")
        sys.exit(1)

    log.info("Wrote %d slices to %s", len(slice_paths), slice_dir)

    # Step 3: Build .adg
    # When --rack-name is provided use it as the filename so that stems and
    # non-stems builds (and different takes) never overwrite each other.
    RACKS_DIR.mkdir(parents=True, exist_ok=True)
    if args.rack_name:
        adg_path = RACKS_DIR / f"{slugify(args.rack_name)}.adg"
    else:
        adg_path = RACKS_DIR / f"{song_slug}_{source_slug}_{today}.adg"
    adg_bytes = build_adg(slice_paths, rack_name, chop_data)
    adg_path.write_bytes(adg_bytes)
    log.info("Drum Rack saved: %s", adg_path)

    # Step 4: Save chop metadata as JSON next to the slices
    meta_path = slice_dir / "chop_metadata.json"
    meta = {
        "song_slug": song_slug,
        "source_file": str(audio_path.resolve()),
        "date": today,
        "rack_name": rack_name,
        "adg_path": str(adg_path),
        "slices_dir": str(slice_dir),
        "gemini_model": args.model,
        "chop_strategy": chop_data.get("chop_strategy"),
        "duration_seconds": chop_data.get("duration_seconds"),
        "chops": chop_data.get("chops", []),
        "slices": [str(p) for p in slice_paths],
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    log.info("Chop metadata saved: %s", meta_path)

    # Step 5: Optionally push slices to GCS
    if args.push_gcs:
        push_slices_to_gcs(slice_dir, song_slug)

    print(f"\nDrum Rack ready: {adg_path}")
    print(f"Slices: {slice_dir} ({len(slice_paths)} files)")

    # Step 6 (optional): auto-load into Ableton
    if args.load_track:
        import subprocess as _sp
        push_script = Path(__file__).parent / "ableton_push.py"
        log.info("Loading '%s' onto Ableton track '%s'...", adg_path.name, args.load_track)
        r = _sp.run(
            [sys.executable, str(push_script), "load-adg",
             "--file", str(adg_path), "--track", args.load_track],
        )
        if r.returncode != 0:
            log.warning("load-adg failed — drag %s into Live manually.", adg_path.name)
        else:
            print(f"Loaded onto Live track '{args.load_track}'.")
    else:
        print(f"Load into Ableton:")
        print(f"  python scripts/ableton_push.py load-adg --file {adg_path} --track <track-name>")

    if not args.push_gcs:
        print(
            f"\nTo push slices to GCS:\n"
            f"  python scripts/gcs_sync.py push {slice_dir}/ --tag {song_slug}"
        )


if __name__ == "__main__":
    main()
