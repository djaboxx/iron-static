#!/usr/bin/env python3
"""
manage_songs.py — IRON STATIC song lifecycle manager.

Manages database/songs.json. Commands:
  add       Add a new song (status: in-progress)
  activate  Set a song as the active song (clears previous active)
  release   Mark a song as released
  archive   Archive a song
  list      List all songs with their status
  active    Print the current active song slug (useful for scripts)

Usage:
  python scripts/manage_songs.py add --slug my-song --title "My Song"
  python scripts/manage_songs.py add --slug my-song --title "My Song" --bpm 140 --key E --scale phrygian
  python scripts/manage_songs.py activate --slug my-song
  python scripts/manage_songs.py release --slug my-song
  python scripts/manage_songs.py archive --slug my-song --reason "B-side, shelved"
  python scripts/manage_songs.py list
  python scripts/manage_songs.py active
"""
import argparse
import json
import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)
DB_PATH = Path(__file__).parent.parent / "database" / "songs.json"


def load_db() -> dict:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Songs database not found: {DB_PATH}")
    with DB_PATH.open() as f:
        return json.load(f)


def save_db(db: dict) -> None:
    with DB_PATH.open("w") as f:
        json.dump(db, f, indent=2)
    log.info("Saved %s", DB_PATH)


def find_song(songs: list, slug: str) -> dict | None:
    return next((s for s in songs if s["slug"] == slug), None)


def cmd_add(args, db: dict) -> None:
    songs = db["songs"]
    if find_song(songs, args.slug):
        log.error("Song '%s' already exists. Use a different slug.", args.slug)
        sys.exit(1)
    song = {
        "slug": args.slug,
        "title": args.title,
        "status": "in-progress",
        "als_path": args.als_path,
        "key": args.key,
        "scale": args.scale,
        "bpm": args.bpm,
        "time_signature": args.time_signature,
        "notes": args.notes or "",
        "outputs": [],
    }
    songs.append(song)
    save_db(db)
    print(f"Added song: {args.slug} ({args.title}) [in-progress]")
    print(f"  To activate: python scripts/manage_songs.py activate --slug {args.slug}")


def cmd_activate(args, db: dict) -> None:
    songs = db["songs"]
    target = find_song(songs, args.slug)
    if not target:
        log.error("Song '%s' not found.", args.slug)
        sys.exit(1)

    # Deactivate any currently active song
    previously_active = []
    for s in songs:
        if s["status"] == "active" and s["slug"] != args.slug:
            s["status"] = "in-progress"
            previously_active.append(s["slug"])

    target["status"] = "active"
    save_db(db)

    if previously_active:
        print(f"Deactivated: {', '.join(previously_active)} → in-progress")
    print(f"Activated: {args.slug} ({target['title']})")


def cmd_release(args, db: dict) -> None:
    songs = db["songs"]
    target = find_song(songs, args.slug)
    if not target:
        log.error("Song '%s' not found.", args.slug)
        sys.exit(1)
    target["status"] = "released"
    if args.notes:
        target["notes"] = (target.get("notes") or "") + f"\n\nRelease note: {args.notes}"
    save_db(db)
    print(f"Released: {args.slug} ({target['title']})")
    print("  The song is no longer active. Add a new song or activate another in-progress song.")


def cmd_archive(args, db: dict) -> None:
    songs = db["songs"]
    target = find_song(songs, args.slug)
    if not target:
        log.error("Song '%s' not found.", args.slug)
        sys.exit(1)
    target["status"] = "archived"
    if args.reason:
        target["archived_reason"] = args.reason
    save_db(db)
    print(f"Archived: {args.slug} ({target['title']})")


def cmd_list(args, db: dict) -> None:
    songs = db["songs"]
    if not songs:
        print("No songs registered.")
        return

    # Group by status for display order
    order = ["active", "in-progress", "released", "archived"]
    grouped = {s: [] for s in order}
    for song in songs:
        grouped.get(song["status"], grouped["archived"]).append(song)

    for status in order:
        group = grouped[status]
        if not group:
            continue
        label = {"active": "ACTIVE", "in-progress": "IN PROGRESS", "released": "RELEASED", "archived": "ARCHIVED"}[status]
        print(f"\n[{label}]")
        for s in group:
            key_info = f" — {s['key']} {s['scale']}" if s.get("key") else ""
            bpm_info = f" @ {s['bpm']}bpm" if s.get("bpm") else ""
            print(f"  {s['slug']}: {s['title']}{key_info}{bpm_info}")


def cmd_active(args, db: dict) -> None:
    songs = db["songs"]
    active = find_song(songs, "") or next((s for s in songs if s["status"] == "active"), None)
    if not active:
        print("none")
        sys.exit(0)
    print(active["slug"])


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="IRON STATIC song lifecycle manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = sub.add_parser("add", help="Add a new song (status: in-progress)")
    p_add.add_argument("--slug", required=True, help="URL-safe identifier, e.g. dead-channel")
    p_add.add_argument("--title", required=True, help="Human-readable song title")
    p_add.add_argument("--als-path", help="Path to .als file, e.g. ableton/sessions/dead-channel_v1.als")
    p_add.add_argument("--key", help="Root key, e.g. E")
    p_add.add_argument("--scale", help="Scale/mode, e.g. phrygian")
    p_add.add_argument("--bpm", type=float, help="Tempo in BPM")
    p_add.add_argument("--time-signature", help="Time signature, e.g. 7/8")
    p_add.add_argument("--notes", help="Free-form notes about the song")

    # activate
    p_act = sub.add_parser("activate", help="Set a song as the active song")
    p_act.add_argument("--slug", required=True)

    # release
    p_rel = sub.add_parser("release", help="Mark a song as released")
    p_rel.add_argument("--slug", required=True)
    p_rel.add_argument("--notes", help="Optional release notes")

    # archive
    p_arc = sub.add_parser("archive", help="Archive a song")
    p_arc.add_argument("--slug", required=True)
    p_arc.add_argument("--reason", help="Why this song is being archived")

    # list
    sub.add_parser("list", help="List all songs with their status")

    # active
    sub.add_parser("active", help="Print the current active song slug")

    args = parser.parse_args()
    db = load_db()

    dispatch = {
        "add": cmd_add,
        "activate": cmd_activate,
        "release": cmd_release,
        "archive": cmd_archive,
        "list": cmd_list,
        "active": cmd_active,
    }
    dispatch[args.command](args, db)


if __name__ == "__main__":
    main()
