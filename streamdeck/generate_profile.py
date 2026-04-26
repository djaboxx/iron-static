#!/usr/bin/env python3
"""
generate_profile.py — Programmatically build the IRON STATIC Stream Deck profile.

Creates:
  1. streamdeck/commands/*.command  — macOS wrapper files Terminal opens + runs
  2. ~/.../ProfilesV3/{UUID}.sdProfile/  — the actual Stream Deck profile dir

Usage:
  python streamdeck/generate_profile.py          # generate files, print install path
  python streamdeck/generate_profile.py --install # also copy to ProfilesV3 dir
  python streamdeck/generate_profile.py --restart # install + restart Stream Deck app

Stream Deck + layout (4 cols × 2 rows):
  [01 Session Start] [02 Git Commit   ] [03 Ableton Launch] [04 VELA Generate]
  [05 Run Brainstorm] [06 GCS Push    ] [07 Transport     ] [08 Health Check ]

Encoders (4 dials) — button-press actions:
  Dial 1 press: BPM tap / session info
  Dial 2 press: open bridge status
  Dial 3 press: Pigments M1 reset
  Dial 4 press: Pigments M2 reset
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("generate_profile")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
STREAMDECK_DIR = REPO_ROOT / "streamdeck"
COMMANDS_DIR = STREAMDECK_DIR / "commands"
PROFILES_V2_DIR = Path.home() / "Library/Application Support/com.elgato.StreamDeck/ProfilesV3"

DEVICE_UUID = "@(1)[4057/132/A00WA4241269CJ]"
DEVICE_MODEL = "20GBD9901"

PROFILE_NAME = "IRON STATIC"
PAGE_NAME = "Main"

# Fixed UUIDs so the profile is stable across re-runs (deterministic, not random).
# If you want a fresh UUID each time, replace with str(uuid.uuid4()).
PROFILE_UUID = "D4C1A9B3-8F2E-4A7D-B650-1E3F9C2D5847"
PAGE_UUID = "A7B2C3D4-E5F6-4A8B-9C0D-1E2F3A4B5C6D"

# ---------------------------------------------------------------------------
# Button definitions: (col, row) → {name, script, title, color}
# ---------------------------------------------------------------------------

BUTTONS = [
    {
        "coord": "0,0",
        "name": "Session Start",
        "script": "01_session_start.sh",
        "command": "01_session_start.command",
        "title": "Session\nStart",
        "color": "#00ff88",
    },
    {
        "coord": "1,0",
        "name": "Git Commit",
        "script": "02_git_commit.sh",
        "command": "02_git_commit.command",
        "title": "Git\nCommit",
        "color": "#ff9900",
    },
    {
        "coord": "2,0",
        "name": "Ableton Launch",
        "script": "03_ableton_launch.sh",
        "command": "03_ableton_launch.command",
        "title": "Ableton\nLaunch",
        "color": "#ff4444",
    },
    {
        "coord": "3,0",
        "name": "VELA Generate",
        "script": "04_vela_generate.sh",
        "command": "04_vela_generate.command",
        "title": "VELA\nGenerate",
        "color": "#cc44ff",
    },
    {
        "coord": "0,1",
        "name": "Run Brainstorm",
        "script": "05_run_brainstorm.sh",
        "command": "05_run_brainstorm.command",
        "title": "Brain-\nstorm",
        "color": "#44aaff",
    },
    {
        "coord": "1,1",
        "name": "GCS Push",
        "script": "06_gcs_push.sh",
        "command": "06_gcs_push.command",
        "title": "GCS\nPush",
        "color": "#ffff44",
    },
    {
        "coord": "2,1",
        "name": "Transport Toggle",
        "script": "07_transport_toggle.sh",
        "command": "07_transport_toggle.command",
        "title": "Transport\nToggle",
        "color": "#ff6600",
    },
    {
        "coord": "3,1",
        "name": "Health Check",
        "script": "08_health_check.sh",
        "command": "08_health_check.command",
        "title": "Health\nCheck",
        "color": "#00ffff",
    },
]

# Encoder button-press actions (dial presses) — run informational/control commands
ENCODER_BUTTONS = [
    {
        "coord": "0,0",
        "name": "BPM",        # matches dialActions key in dial-info.ts
        "command_text": f"cd {REPO_ROOT} && python scripts/manage_songs.py list",
        "title": "BPM",
        "color": "#00ff88",
    },
    {
        "coord": "1,0",
        "name": "Bridge",     # matches dialActions key in dial-info.ts
        "command_text": f"cd {REPO_ROOT} && python scripts/bridge_client.py --ping",
        "title": "Bridge",
        "color": "#ff9900",
    },
    {
        "coord": "2,0",
        "name": "M1",         # matches dialActions key in dial-info.ts
        "command_text": f"cd {REPO_ROOT} && python streamdeck/dial_bridge.py --dial 3 --delta 0",
        "title": "M1",
        "color": "#cc44ff",
    },
    {
        "coord": "3,0",
        "name": "M2",         # matches dialActions key in dial-info.ts
        "command_text": f"cd {REPO_ROOT} && python streamdeck/dial_bridge.py --dial 4 --delta 0",
        "title": "M2",
        "color": "#cc44ff",
    },
]


# ---------------------------------------------------------------------------
# Helper: generate a fresh UUID
# ---------------------------------------------------------------------------

def new_uuid() -> str:
    return str(uuid.uuid4()).upper()


# ---------------------------------------------------------------------------
# Build .command wrapper files
# ---------------------------------------------------------------------------

def build_command_files() -> None:
    """Create macOS .command files that wrap the button shell scripts.

    macOS Terminal opens .command files and executes them automatically —
    this is how we launch our scripts from Stream Deck's system.open action.
    """
    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)

    for btn in BUTTONS:
        script_path = STREAMDECK_DIR / "buttons" / btn["script"]
        command_path = COMMANDS_DIR / btn["command"]

        content = f"""#!/usr/bin/env zsh
# IRON STATIC Stream Deck command wrapper — auto-generated by generate_profile.py
# Button: {btn["name"]}
exec "{script_path}"
"""
        command_path.write_text(content)
        command_path.chmod(0o755)
        log.info("Wrote %s", command_path)

    # Also create encoder command files
    for enc in ENCODER_BUTTONS:
        command_path = COMMANDS_DIR / f"enc_{enc['coord'].replace(',', '_')}_{enc['name'].lower().replace(' ', '_')}.command"
        content = f"""#!/usr/bin/env zsh
# IRON STATIC Stream Deck encoder command — auto-generated by generate_profile.py
# Encoder: {enc["name"]}
source ~/.zshrc 2>/dev/null
{enc["command_text"]}
"""
        command_path.write_text(content)
        command_path.chmod(0o755)
        log.info("Wrote %s", command_path)


# ---------------------------------------------------------------------------
# Build action objects using the IRON STATIC Bridge plugin
# ---------------------------------------------------------------------------

BRIDGE_RUN_SCRIPT_UUID = "com.iron-static.bridge.run-script"
BRIDGE_DIAL_INFO_UUID = "com.iron-static.bridge.dial-info"


def make_bridge_run_action(name: str, script: str, title: str, color: str) -> dict:
    """Keypad button → runs streamdeck/buttons/<script>.sh silently via the bridge plugin."""
    return {
        "ActionID": new_uuid(),
        "LinkedTitle": False,
        "Name": name,
        "Settings": {
            "script": script,
        },
        "State": 0,
        "States": [
            {
                "FontFamily": "",
                "FontSize": 12,
                "FontStyle": "Bold",
                "FontUnderline": False,
                "OutlineThickness": 2,
                "ShowTitle": True,
                "Title": title,
                "TitleAlignment": "bottom",
                "TitleColor": color,
            }
        ],
        "UUID": BRIDGE_RUN_SCRIPT_UUID,
    }


def make_bridge_dial_action(label: str, title: str, color: str) -> dict:
    """Encoder slot → displays live info on the touchscreen strip via the bridge plugin."""
    return {
        "ActionID": new_uuid(),
        "LinkedTitle": False,
        "Name": label,
        "Settings": {
            "label": label,
        },
        "State": 0,
        "States": [
            {
                "FontSize": 10,
                "FontStyle": "Bold",
                "ShowTitle": True,
                "Title": title,
                "TitleAlignment": "bottom",
                "TitleColor": color,
            }
        ],
        "UUID": BRIDGE_DIAL_INFO_UUID,
    }


# ---------------------------------------------------------------------------
# Build the page manifest
# ---------------------------------------------------------------------------

def build_page_manifest() -> dict:
    keypad_actions = {}
    for btn in BUTTONS:
        action = make_bridge_run_action(
            name=btn["name"],
            script=btn["script"].replace(".sh", ""),
            title=btn["title"],
            color=btn["color"],
        )
        keypad_actions[btn["coord"]] = action

    encoder_actions = {}
    for enc in ENCODER_BUTTONS:
        action = make_bridge_dial_action(
            label=enc["name"],
            title=enc["title"],
            color=enc["color"],
        )
        encoder_actions[enc["coord"]] = action

    return {
        "Controllers": [
            {
                "Actions": encoder_actions,
                "Type": "Encoder",
            },
            {
                "Actions": keypad_actions,
                "Type": "Keypad",
            },
        ],
        "Icon": "",
        "Name": PAGE_NAME,
    }


# ---------------------------------------------------------------------------
# Build the top-level profile manifest
# ---------------------------------------------------------------------------

def build_profile_manifest() -> dict:
    return {
        "AppIdentifier": "*",
        "Device": {
            "Model": DEVICE_MODEL,
            "UUID": DEVICE_UUID,
        },
        "Name": PROFILE_NAME,
        "Pages": {
            "Current": PAGE_UUID,
            "Default": PAGE_UUID,
            "Pages": [PAGE_UUID],
        },
        "Version": "3.0",
    }


# ---------------------------------------------------------------------------
# Write the .sdProfile directory to a target location
# ---------------------------------------------------------------------------

def write_profile(target_dir: Path) -> Path:
    """Write the complete .sdProfile directory structure to target_dir."""
    profile_dir = target_dir / f"{PROFILE_UUID}.sdProfile"
    page_dir = profile_dir / "Profiles" / PAGE_UUID

    # Always remove first — macOS case-insensitive FS will reuse stale lowercase dirs
    if profile_dir.exists():
        shutil.rmtree(profile_dir)
    page_dir.mkdir(parents=True, exist_ok=True)

    # Top-level manifest
    profile_manifest_path = profile_dir / "manifest.json"
    profile_manifest_path.write_text(
        json.dumps(build_profile_manifest(), indent=2)
    )
    log.info("Wrote %s", profile_manifest_path)

    # Page manifest
    page_manifest_path = page_dir / "manifest.json"
    page_manifest_path.write_text(
        json.dumps(build_page_manifest(), indent=2)
    )
    log.info("Wrote %s", page_manifest_path)

    return profile_dir


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate IRON STATIC Stream Deck profile"
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Copy profile to ProfilesV3 (makes it visible in Stream Deck app)",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Install + restart Stream Deck app to load the profile",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=STREAMDECK_DIR / "profile_output",
        help="Output directory for generated profile (default: streamdeck/profile_output/)",
    )
    args = parser.parse_args()

    if args.restart:
        args.install = True

    # Step 1: build .command wrapper files (kept as legacy fallback; profile now uses bridge plugin)
    log.info("Building .command fallback files in %s", COMMANDS_DIR)
    build_command_files()

    # Step 2: write profile to output directory
    log.info("Writing profile to %s", args.output)
    args.output.mkdir(parents=True, exist_ok=True)
    profile_dir = write_profile(args.output)
    log.info("Profile written: %s", profile_dir)

    # Step 3: optionally install to ProfilesV3
    if args.install:
        dest = PROFILES_V2_DIR / f"{PROFILE_UUID}.sdProfile"
        if dest.exists():
            log.info("Removing existing profile at %s", dest)
            shutil.rmtree(dest)
        shutil.copytree(profile_dir, dest)
        log.info("Installed to %s", dest)
    else:
        log.info("")
        log.info("To install manually:")
        log.info("  cp -r '%s' '%s/'", profile_dir, PROFILES_V2_DIR)
        log.info("")
        log.info("Or re-run with --install:")
        log.info("  python streamdeck/generate_profile.py --install")

    # Step 4: optionally restart Stream Deck
    if args.restart:
        log.info("Restarting Stream Deck app...")
        subprocess.run(
            ["osascript", "-e", 'quit app "Elgato Stream Deck"'],
            check=False,
        )
        import time
        time.sleep(2)
        subprocess.run(
            ["open", "-a", "Elgato Stream Deck"],
            check=False,
        )
        log.info("Stream Deck restarted.")

    log.info("")
    log.info("Done. Profile UUID: %s", PROFILE_UUID)
    log.info("Profile name: %s", PROFILE_NAME)
    log.info("Device UUID: %s", DEVICE_UUID)


if __name__ == "__main__":
    main()
