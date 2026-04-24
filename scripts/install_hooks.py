#!/usr/bin/env python3
"""
Install iron-static git hooks by pointing git's hooksPath at .github/hooks/.
Run once after cloning:  python scripts/install_hooks.py
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO_ROOT / ".github" / "hooks"


def main():
    # Make all hooks executable
    for hook in HOOKS_DIR.iterdir():
        if hook.is_file() and not hook.name.endswith((".md", ".py", ".txt")):
            hook.chmod(0o755)
            print(f"  chmod +x {hook.relative_to(REPO_ROOT)}")

    # Point git at the hooks directory
    result = subprocess.run(
        ["git", "config", "core.hooksPath", str(HOOKS_DIR.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT
    )
    if result.returncode != 0:
        print("ERROR: failed to set core.hooksPath", file=sys.stderr)
        sys.exit(1)

    print(f"\nHooks installed. git will use: {HOOKS_DIR.relative_to(REPO_ROOT)}/")
    print("Active hooks:")
    for hook in sorted(HOOKS_DIR.iterdir()):
        if hook.is_file() and not hook.name.endswith((".md", ".py", ".txt")):
            print(f"  {hook.name}")


if __name__ == "__main__":
    main()
