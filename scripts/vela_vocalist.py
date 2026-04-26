#!/usr/bin/env python3
"""
vela_vocalist.py — ACE-Step API wrapper for VELA vocal generation.

VELA's singing/melodic voice. Reads active song context from database/songs.json
and LoRA config from database/voices.json.

Usage:
    python scripts/vela_vocalist.py render --song ignition-point --lyrics "Ignition. The system knows."
    python scripts/vela_vocalist.py render --song ignition-point --phrases-file midi/sequences/ignition-point_vocal-phrases.json
    python scripts/vela_vocalist.py status --task-id <task_id>
    python scripts/vela_vocalist.py health

ACE-Step API server must be running at localhost:8001.
Start it with: cd ~/tools/ACE-Step-1.5 && nohup ./start_api_server_macos.sh > /tmp/acestep-api.log 2>&1 &
"""

import argparse
import json
import logging
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
VOICES_DB = REPO_ROOT / "database" / "voices.json"
SONGS_DB = REPO_ROOT / "database" / "songs.json"
VOCALS_OUT = REPO_ROOT / "audio" / "samples" / "vocals" / "vela"
ACESTEP_BASE = "http://127.0.0.1:8001"
POLL_INTERVAL = 5  # seconds between status polls
POLL_TIMEOUT = 600  # 10 minutes max


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _post_json(url: str, payload: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_active_song() -> dict:
    db = _load_json(SONGS_DB)
    for song in db.get("songs", []):
        if song.get("status") == "active":
            return song
    return {}


def get_vela_config() -> dict:
    db = _load_json(VOICES_DB)
    return db.get("voices", {}).get("vela", {})


def cmd_health(_args) -> None:
    try:
        result = _get_json(f"{ACESTEP_BASE}/health")
        data = result.get("data", {})
        initialized = data.get("models_initialized", False)
        status = data.get("status", "unknown")
        model = data.get("loaded_model", "unknown")
        log.info("ACE-Step API: %s | model=%s | initialized=%s", status, model, initialized)
        if not initialized:
            log.info("Models will load on first generation request (~10GB download on first run).")
    except Exception as e:
        log.error("Cannot reach ACE-Step API at %s: %s", ACESTEP_BASE, e)
        log.error("Start server: cd ~/tools/ACE-Step-1.5 && nohup ./start_api_server_macos.sh > /tmp/acestep-api.log 2>&1 &")
        sys.exit(1)


def cmd_status(args) -> None:
    task_id = args.task_id
    payload = {"task_ids": [task_id]}
    result = _post_json(f"{ACESTEP_BASE}/query_result", payload)
    data = result.get("data", {})
    task = data.get(task_id, {})
    status = task.get("status")
    STATUS_MAP = {0: "queued/processing", 1: "succeeded", 2: "failed", 3: "cancelled"}
    log.info("Task %s: %s", task_id, STATUS_MAP.get(status, f"unknown({status})"))
    if status == 1:
        for item in task.get("result", []):
            log.info("  Audio: %s", item.get("audio_url") or item.get("path"))
    elif status == 2:
        log.error("  Error: %s", task.get("error_message", "unknown"))


def _build_prompt(vela: dict, song: dict) -> str:
    tags = vela.get("character_tags", "cold androgynous voice, industrial metal, mechanical, sparse vocals, declaratory, dry, stark")
    # Add song-context tags
    scale = song.get("scale", "")
    if scale:
        tags = f"{tags}, {scale} scale"
    return tags


def _poll_task(task_id: str, label: str) -> dict | None:
    """Poll until task completes or times out. Returns result dict or None on failure."""
    deadline = time.time() + POLL_TIMEOUT
    log.info("Polling task %s (%s)...", task_id, label)
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        result = _post_json(f"{ACESTEP_BASE}/query_result", {"task_ids": [task_id]}, timeout=120)
        task = result.get("data", {}).get(task_id, {})
        status = task.get("status")
        if status == 1:
            log.info("Task %s completed.", task_id)
            return task
        elif status == 2:
            log.error("Task %s failed: %s", task_id, task.get("error_message", "unknown"))
            return None
        elif status == 3:
            log.error("Task %s cancelled.", task_id)
            return None
        else:
            log.info("  ...still processing (status=%s)", status)
    log.error("Task %s timed out after %ds.", task_id, POLL_TIMEOUT)
    return None


def _download_audio(audio_url: str, dest: Path) -> bool:
    """Download audio from ACE-Step server to local path."""
    # audio_url may be relative (e.g. /v1/audio?path=...) or absolute
    if audio_url.startswith("http"):
        url = audio_url
    else:
        url = f"{ACESTEP_BASE}{audio_url}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlretrieve(url, str(dest))
        log.info("  Saved: %s", dest)
        return True
    except Exception as e:
        log.error("  Download failed (%s): %s", url, e)
        return False


def cmd_render(args) -> None:
    # Resolve song
    if args.song:
        db = _load_json(SONGS_DB)
        song = next((s for s in db.get("songs", []) if s["slug"] == args.song), None)
        if song is None:
            log.error("Song not found: %s", args.song)
            sys.exit(1)
    else:
        song = get_active_song()
        if not song:
            log.error("No active song. Use --song <slug> or activate one with manage_songs.py.")
            sys.exit(1)

    vela = get_vela_config()
    if not vela:
        log.error("No 'vela' entry in database/voices.json.")
        sys.exit(1)

    song_slug = song["slug"]
    bpm = song.get("bpm")
    key = song.get("key", "")
    scale = song.get("scale", "")
    key_scale_str = f"{key} {scale}".strip() if key else ""

    # Resolve lyrics
    if args.lyrics:
        phrases = [("phrase", args.lyrics)]
    elif args.phrases_file:
        pf = Path(args.phrases_file)
        if not pf.exists():
            log.error("Phrases file not found: %s", pf)
            sys.exit(1)
        raw = _load_json(pf)
        # Expect list of {"label": ..., "lyrics": ...} or list of strings
        if isinstance(raw, list):
            phrases = []
            for item in raw:
                if isinstance(item, str):
                    phrases.append(("phrase", item))
                else:
                    phrases.append((item.get("label", "phrase"), item.get("lyrics", "")))
        else:
            log.error("Phrases file must be a JSON array.")
            sys.exit(1)
    else:
        log.error("Provide --lyrics or --phrases-file.")
        sys.exit(1)

    prompt = _build_prompt(vela, song)
    lora_path = vela.get("lora_path")
    lora_name = vela.get("lora_name")
    out_dir = VOCALS_OUT / song_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("Song: %s (%s, %s BPM)", song.get("title", song_slug), key_scale_str, bpm)
    log.info("Prompt tags: %s", prompt)
    if lora_name:
        log.info("LoRA: %s", lora_name)
    else:
        log.info("No LoRA trained yet — generating with character tags only.")

    duration = args.duration or 30.0

    for label, lyrics in phrases:
        if not lyrics.strip():
            continue
        log.info("Submitting: [%s] '%s...'", label, lyrics[:50])

        payload = {
            "prompt": prompt,
            "lyrics": lyrics,
            "audio_format": "wav",
            "audio_duration": duration,
            "batch_size": args.batch_size,
            "vocal_language": "en",
        }
        if bpm:
            payload["bpm"] = int(bpm)
        if key_scale_str:
            payload["key_scale"] = key_scale_str
        if lora_name:
            payload["lora_name_or_path"] = lora_name
        elif lora_path:
            payload["lora_name_or_path"] = lora_path

        # Submit generation task
        result = _post_json(f"{ACESTEP_BASE}/release_task", payload)
        if result.get("code") != 200:
            log.error("Task submission failed: %s", result.get("error"))
            continue
        task_id = result["data"]["task_id"]
        log.info("Task ID: %s", task_id)

        # Poll to completion
        task = _poll_task(task_id, label)
        if task is None:
            continue

        # Download outputs
        safe_label = label.replace(" ", "_").replace("/", "-")
        results = task.get("result", [])
        for i, item in enumerate(results):
            audio_url = item.get("audio_url") or item.get("path")
            if not audio_url:
                continue
            suffix = f"_{i+1}" if len(results) > 1 else ""
            dest = out_dir / f"{safe_label}_vela{suffix}.wav"
            _download_audio(audio_url, dest)

        # Optional: extract clean vocal stem
        if args.extract_stems and results:
            first_url = results[0].get("audio_url") or results[0].get("path")
            if first_url:
                log.info("Extracting vocal stem for %s...", label)
                extract_payload = {
                    "task_type": "extract",
                    "src_audio_path": results[0].get("path", ""),
                    "prompt": prompt,
                    "audio_format": "wav",
                }
                # Only works if the server has the file path; skip if only URL
                if results[0].get("path"):
                    ex_result = _post_json(f"{ACESTEP_BASE}/release_task", extract_payload)
                    if ex_result.get("code") == 200:
                        ex_task_id = ex_result["data"]["task_id"]
                        ex_task = _poll_task(ex_task_id, f"{label}_stem")
                        if ex_task:
                            for j, ex_item in enumerate(ex_task.get("result", [])):
                                ex_url = ex_item.get("audio_url") or ex_item.get("path")
                                if ex_url:
                                    dest = out_dir / f"{safe_label}_vela_stem.wav"
                                    _download_audio(ex_url, dest)

    log.info("Done. Vocals in: %s", out_dir)


def main():
    parser = argparse.ArgumentParser(
        description="VELA vocal generator — ACE-Step API wrapper for IRON STATIC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # health
    sub.add_parser("health", help="Check ACE-Step API server status")

    # status
    p_status = sub.add_parser("status", help="Check status of a submitted task")
    p_status.add_argument("--task-id", required=True, help="Task ID from a prior render call")

    # render
    p_render = sub.add_parser("render", help="Generate VELA vocals for a song phrase")
    p_render.add_argument("--song", help="Song slug (default: active song)")
    p_render.add_argument("--lyrics", help="Lyrics string for a single phrase")
    p_render.add_argument("--phrases-file", help="JSON array of {label, lyrics} objects")
    p_render.add_argument("--duration", type=float, default=30.0, help="Target audio duration in seconds (default: 30)")
    p_render.add_argument("--batch-size", type=int, default=3, help="Variations to generate per phrase (default: 3)")
    p_render.add_argument("--extract-stems", action="store_true", help="Also extract clean vocal stem via ACE-Step extract task")

    args = parser.parse_args()
    dispatch = {"health": cmd_health, "status": cmd_status, "render": cmd_render}
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
