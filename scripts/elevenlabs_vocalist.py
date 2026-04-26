#!/usr/bin/env python3
"""
elevenlabs_vocalist.py — Design and render the IRON STATIC vocalist via ElevenLabs.

The vocalist is a named voice with a fixed character — not a generic TTS call.
Once designed and saved, it is referenced by voice_id in the manifest so all
future renders are consistent.

Subcommands:
  design    Generate voice previews from a text description, pick one, save it.
  render    Render phrases to WAV files using the saved voice.
  list      List voices saved in the manifest.

Usage:
  python scripts/elevenlabs_vocalist.py design --name "IRON_STATIC_VOCALIST" [--gender neutral] [--age middle_aged] [--accent american] [--description "..."]
  python scripts/elevenlabs_vocalist.py render --voice-id <id> --phrases <file.json> --song ignition-point
  python scripts/elevenlabs_vocalist.py render --voice-id <id> --text "ignition" --song ignition-point
  python scripts/elevenlabs_vocalist.py list

Environment:
  ELEVEN_LABS_TOKEN  — required

Output:
  audio/samples/vocals/elevenlabs/[song-slug]/[phrase]_[voice-name].wav
  database/voices.json — manifest of saved voices
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
VOICES_DB = REPO_ROOT / "database" / "voices.json"

# Default voice character for IRON STATIC — designed to sit between human and machine.
# Cold, precise, androgynous, declaratory. Not singing. Announcing the end of something.
DEFAULT_VOICE_DESCRIPTION = (
    "A cold, precise, androgynous voice with a slight mechanical edge. "
    "Declaratory rather than conversational — each word lands with weight and finality. "
    "Dry delivery, minimal warmth, controlled breath. "
    "The voice of a system that has stopped pretending to care, but has not yet stopped working. "
    "Industrial. Urgent. Human enough to be unsettling."
)

DEFAULT_SAMPLE_TEXT = (
    "Ignition. The system knows. No trace. Phase transition. "
    "Cannot be read. Control. The machine does not forget."
)


def _client():
    api_key = os.environ.get("ELEVEN_LABS_TOKEN")
    if not api_key:
        log.error("ELEVEN_LABS_TOKEN not set.")
        sys.exit(1)
    from elevenlabs import ElevenLabs
    return ElevenLabs(api_key=api_key)


def _load_voices_db() -> dict:
    if VOICES_DB.exists():
        return json.loads(VOICES_DB.read_text())
    return {"voices": {}}


def _save_voices_db(db: dict):
    VOICES_DB.parent.mkdir(parents=True, exist_ok=True)
    VOICES_DB.write_text(json.dumps(db, indent=2))
    log.info("Saved voice manifest: %s", VOICES_DB.relative_to(REPO_ROOT))


def cmd_design(args):
    """Generate voice previews, let user pick one, save to manifest."""
    client = _client()

    description = args.description or DEFAULT_VOICE_DESCRIPTION
    log.info("Generating voice previews for: %s", args.name)
    log.info("Description: %s", description)

    previews = client.text_to_voice.create_previews(
        voice_description=description,
        text=DEFAULT_SAMPLE_TEXT,
    )

    if not previews.previews:
        log.error("No previews returned.")
        sys.exit(1)

    # Save preview audio files for listening
    preview_dir = REPO_ROOT / "audio" / "samples" / "vocals" / "elevenlabs" / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{len(previews.previews)} previews generated:\n")
    for i, preview in enumerate(previews.previews):
        out = preview_dir / f"preview_{i:02d}_{args.name}.mp3"
        # preview.audio_base_64 is base64-encoded MP3
        import base64
        out.write_bytes(base64.b64decode(preview.audio_base_64))
        print(f"  [{i}] {out.name}  (generated_voice_id: {preview.generated_voice_id})")

    print(f"\nPreviews saved to: {preview_dir}")
    print("Open them in Finder, listen, then enter the number to save:\n")

    choice = input(f"Pick preview [0-{len(previews.previews)-1}] (or 'q' to quit): ").strip()
    if choice.lower() == "q":
        log.info("Aborted.")
        return

    idx = int(choice)
    chosen = previews.previews[idx]

    log.info("Saving voice '%s' from preview %d...", args.name, idx)
    saved = client.text_to_voice.create(
        voice_name=args.name,
        voice_description=description,
        generated_voice_id=chosen.generated_voice_id,
    )

    voice_id = saved.voice_id
    log.info("Voice saved. voice_id: %s", voice_id)

    db = _load_voices_db()
    db["voices"][args.name] = {
        "voice_id": voice_id,
        "name": args.name,
        "description": description,
        "preview_idx": idx,
        "generated_voice_id": chosen.generated_voice_id,
    }
    _save_voices_db(db)

    print(f"\nVoice ID: {voice_id}")
    print(f"Use: python scripts/elevenlabs_vocalist.py render --voice-id {voice_id} --song <slug>")


def cmd_render(args):
    """Render phrases to WAV files using a saved voice."""
    client = _client()

    # Resolve voice_id — name or explicit ID
    voice_id = args.voice_id
    if not voice_id:
        db = _load_voices_db()
        if args.name and args.name in db["voices"]:
            voice_id = db["voices"][args.name]["voice_id"]
            voice_label = args.name
        elif db["voices"]:
            # Use first saved voice
            voice_label, meta = next(iter(db["voices"].items()))
            voice_id = meta["voice_id"]
            log.info("No --voice-id given, using first saved voice: %s (%s)", voice_label, voice_id)
        else:
            log.error("No voice_id provided and no voices in manifest. Run 'design' first.")
            sys.exit(1)
    else:
        # Find label for this voice_id from DB
        db = _load_voices_db()
        voice_label = next(
            (name for name, meta in db["voices"].items() if meta["voice_id"] == voice_id),
            voice_id[:8],
        )

    # Build phrase list
    phrases = []
    if args.text:
        phrases = [args.text.strip()]
    elif args.phrases:
        p = Path(args.phrases)
        if not p.exists():
            log.error("Phrases file not found: %s", p)
            sys.exit(1)
        data = json.loads(p.read_text())
        # Support {"phrases": [...]} or [...]
        phrases = data.get("phrases", data) if isinstance(data, dict) else data
    else:
        # Default: ignition-point vocabulary
        phrases = [
            "ignition", "control", "the machine", "no trace",
            "phase transition", "the system knows", "ah oh ee",
            "erase", "cannot be read", "no record", "not the data",
            "solid to gas", "awake", "ih ah",
        ]
        log.info("No phrases specified — using ignition-point default vocabulary (%d phrases)", len(phrases))

    slug = args.song or "unknown"
    out_dir = REPO_ROOT / "audio" / "samples" / "vocals" / "elevenlabs" / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    model_id = args.model or "eleven_multilingual_v2"
    label = voice_label.lower().replace(" ", "-")

    log.info("Rendering %d phrase(s) → %s", len(phrases), out_dir.relative_to(REPO_ROOT))

    for phrase in phrases:
        slug_phrase = phrase.lower().replace(" ", "-").replace("'", "").replace("/", "-")
        out_path = out_dir / f"{slug_phrase}_{label}.wav"

        if out_path.exists() and not args.force:
            log.info("  skip (exists): %s", out_path.name)
            continue

        log.info("  render: %s → %s", phrase, out_path.name)

        audio_iter = client.text_to_speech.convert(
            voice_id=voice_id,
            text=phrase,
            model_id=model_id,
            output_format="pcm_44100",  # raw PCM → we'll wrap in WAV
        )

        # Collect PCM bytes
        pcm_bytes = b"".join(audio_iter)

        # Write as WAV (16-bit, 44100Hz, mono)
        import wave, struct
        with wave.open(str(out_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(44100)
            wf.writeframes(pcm_bytes)

    log.info("Done. Output: %s", out_dir.relative_to(REPO_ROOT))
    print(f"\nRendered to: {out_dir}")
    print(f"Next: python scripts/chop_and_rack.py --file <wav> --slices 16 --song {slug}")


def cmd_list(args):
    db = _load_voices_db()
    if not db["voices"]:
        print("No voices saved. Run: python scripts/elevenlabs_vocalist.py design --name <name>")
        return
    for name, meta in db["voices"].items():
        print(f"  {name}")
        print(f"    voice_id:    {meta['voice_id']}")
        print(f"    description: {meta['description'][:80]}...")


def main():
    parser = argparse.ArgumentParser(
        description="Design and render the IRON STATIC vocalist via ElevenLabs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # design
    p_design = sub.add_parser("design", help="Generate voice previews and save a voice.")
    p_design.add_argument("--name", default="IRON_STATIC_VOCALIST", help="Name for this voice in the manifest")
    p_design.add_argument("--description", default=None, help="Override default voice description")

    # render
    p_render = sub.add_parser("render", help="Render phrases to WAV using a saved voice.")
    p_render.add_argument("--voice-id", default=None, help="ElevenLabs voice_id (overrides --name lookup)")
    p_render.add_argument("--name", default=None, help="Voice name from manifest (alternative to --voice-id)")
    p_render.add_argument("--song", required=True, help="Song slug (used for output directory)")
    p_render.add_argument("--phrases", default=None, help="Path to JSON file with phrase list")
    p_render.add_argument("--text", default=None, help="Single phrase to render")
    p_render.add_argument("--model", default="eleven_multilingual_v2", help="ElevenLabs model ID")
    p_render.add_argument("--force", action="store_true", help="Re-render even if output exists")

    # list
    sub.add_parser("list", help="List saved voices in the manifest.")

    args = parser.parse_args()

    if args.cmd == "design":
        cmd_design(args)
    elif args.cmd == "render":
        cmd_render(args)
    elif args.cmd == "list":
        cmd_list(args)


if __name__ == "__main__":
    main()
