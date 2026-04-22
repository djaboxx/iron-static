#!/usr/bin/env python3
"""
deploy_remote_script.py — Install IronStatic Remote Script into Ableton Live.

Usage:
    python scripts/deploy_remote_script.py [--app-bundle] [--user-scripts]

    --app-bundle   Install into the app bundle (needed for Live 12.2+ on macOS)
    --user-scripts Also install into User Remote Scripts directory
    (default: --app-bundle only)
"""

import argparse
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
SCRIPT_SRC = REPO_ROOT / "ableton" / "remote_script" / "IronStatic"
APP_BUNDLE_SCRIPTS = Path("/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts")
ABLETON_PREFS = Path.home() / "Library/Preferences/Ableton"


def find_user_scripts_dir():
    """Find the most recently used Ableton version's User Remote Scripts dir."""
    if not ABLETON_PREFS.exists():
        return None
    candidates = sorted(
        [d for d in ABLETON_PREFS.iterdir() if d.is_dir() and d.name.startswith("Live ")],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        user_scripts = candidate / "User Remote Scripts"
        if user_scripts.exists():
            return user_scripts
    return None


def compile_pyc(src_py: Path, dest_dir: Path):
    """Compile src_py to a .pyc and place it as __init__.pyc in dest_dir.
    
    Ableton Live 12 on macOS requires __init__.pyc directly in the script folder
    (old-style Python 2 placement). It uses Python 3.11 internally.
    We compile with whatever Python is available and place the result correctly.
    """
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(src_py)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        log.error("Compile error: %s", result.stderr)
        return False

    # Find the compiled pyc in __pycache__
    pycache = src_py.parent / "__pycache__"
    pyc_files = list(pycache.glob("__init__.cpython-*.pyc"))
    if not pyc_files:
        log.warning("No pyc found in __pycache__ — skipping pyc deployment")
        return False

    dest_pyc = dest_dir / "__init__.pyc"
    shutil.copy2(pyc_files[0], dest_pyc)
    log.info("  Compiled pyc -> %s", dest_pyc)
    return True


def install_to(dest_dir: Path, label: str):
    target = dest_dir / "IronStatic"
    log.info("Installing IronStatic to %s (%s)...", target, label)

    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    # Copy source file
    src_init = SCRIPT_SRC / "__init__.py"
    shutil.copy2(src_init, target / "__init__.py")
    log.info("  Copied __init__.py")

    # Compile and place pyc (required for app bundle / Live 12 discovery)
    compile_pyc(src_init, target)
    log.info("  Done.")


def main():
    parser = argparse.ArgumentParser(description="Deploy IronStatic Remote Script to Ableton")
    parser.add_argument("--app-bundle", action="store_true", default=True,
                        help="Install to app bundle MIDI Remote Scripts (default)")
    parser.add_argument("--user-scripts", action="store_true",
                        help="Also install to User Remote Scripts directory")
    args = parser.parse_args()

    if not SCRIPT_SRC.exists():
        log.error("Source not found: %s", SCRIPT_SRC)
        sys.exit(1)

    if args.app_bundle:
        if not APP_BUNDLE_SCRIPTS.exists():
            log.error("App bundle not found: %s", APP_BUNDLE_SCRIPTS)
        else:
            install_to(APP_BUNDLE_SCRIPTS, "app bundle")

    if args.user_scripts:
        user_dir = find_user_scripts_dir()
        if not user_dir:
            log.warning("Could not find User Remote Scripts directory")
        else:
            install_to(user_dir, "user scripts")

    log.info("")
    log.info("Done. In Ableton: Settings → Link/Tempo/MIDI → Control Surface → select IronStatic")
    log.info("If already selected, deselect and reselect to reload.")


if __name__ == "__main__":
    main()
