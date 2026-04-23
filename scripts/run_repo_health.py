#!/usr/bin/env python3
"""
run_repo_health.py — IRON STATIC repository audit script.

Checks:
  1. Each instrument folder has README.md, at least one file in manuals/, and presets/.
  2. Every slug in instruments/ is registered in database/instruments.json.
  3. Every MIDI-capable instrument with has_memory=true has a JSON in database/midi_params/.
  4. Skills in .github/skills/ don't reference missing files.

Writes:
  outputs/repo_health.json  — machine-readable pass/fail per check
  outputs/repo_health_issues.md — plain-language summary (only if issues found)

Usage:
    python scripts/run_repo_health.py [--no-llm]
    python scripts/run_repo_health.py --out-dir outputs/
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTRUMENTS_DIR = REPO_ROOT / "instruments"
DB_INSTRUMENTS = REPO_ROOT / "database" / "instruments.json"
DB_SONGS = REPO_ROOT / "database" / "songs.json"
MIDI_PARAMS_DIR = REPO_ROOT / "database" / "midi_params"
SKILLS_DIR = REPO_ROOT / ".github" / "skills"
OUTPUTS_DIR = REPO_ROOT / "outputs"


# ---------------------------------------------------------------------------
# Check functions — each returns a list of finding dicts
# ---------------------------------------------------------------------------

def check_instrument_folders() -> list[dict]:
    """Verify each instrument folder has README.md, manuals/ content, and presets/."""
    findings = []
    if not INSTRUMENTS_DIR.exists():
        findings.append({
            "check": "instrument_folders",
            "slug": "_all",
            "status": "fail",
            "detail": "instruments/ directory does not exist",
        })
        return findings

    for folder in sorted(INSTRUMENTS_DIR.iterdir()):
        if not folder.is_dir():
            continue
        slug = folder.name
        base = {"check": "instrument_folders", "slug": slug}

        readme = folder / "README.md"
        if not readme.exists():
            findings.append({**base, "status": "fail", "detail": "Missing README.md"})
        else:
            findings.append({**base, "status": "pass", "detail": "README.md present"})

        manuals = folder / "manuals"
        if not manuals.exists():
            findings.append({**base, "status": "fail", "detail": "Missing manuals/ directory"})
        else:
            manual_files = [f for f in manuals.iterdir() if f.is_file()]
            if not manual_files:
                findings.append({**base, "status": "warn", "detail": "manuals/ directory is empty"})
            else:
                findings.append({
                    **base,
                    "status": "pass",
                    "detail": f"manuals/ has {len(manual_files)} file(s)",
                })

        presets = folder / "presets"
        if not presets.exists():
            findings.append({**base, "status": "fail", "detail": "Missing presets/ directory"})
        else:
            findings.append({**base, "status": "pass", "detail": "presets/ present"})

    return findings


def check_instruments_registered() -> list[dict]:
    """Verify every folder in instruments/ is in database/instruments.json.

    Matches by folder name appearing in any registered instrument's manual_path,
    presets_path, or readme field — since slugs (e.g. 'digitakt') differ from
    folder names (e.g. 'elektron-digitakt-mk1').
    """
    findings = []
    if not DB_INSTRUMENTS.exists():
        findings.append({
            "check": "instruments_registered",
            "slug": "_all",
            "status": "fail",
            "detail": "database/instruments.json does not exist",
        })
        return findings

    db = json.loads(DB_INSTRUMENTS.read_text())

    # Build a set of all path fragments mentioned in instruments.json
    path_mentions: set[str] = set()
    for inst in db.get("instruments", []):
        for field in ("manual_path", "presets_path", "readme"):
            val = inst.get(field, "")
            # Extract the instrument folder name from the path
            parts = Path(val).parts
            if len(parts) >= 2:
                path_mentions.add(parts[1])  # e.g. "elektron-digitakt-mk1"

    for folder in sorted(INSTRUMENTS_DIR.iterdir()):
        if not folder.is_dir():
            continue
        folder_name = folder.name
        if folder_name in path_mentions:
            findings.append({
                "check": "instruments_registered",
                "slug": folder_name,
                "status": "pass",
                "detail": "Referenced in instruments.json",
            })
        else:
            findings.append({
                "check": "instruments_registered",
                "slug": folder_name,
                "status": "fail",
                "detail": "Not referenced in database/instruments.json",
            })
    return findings


def check_midi_params() -> list[dict]:
    """Verify instruments with has_memory=true have a midi_params JSON."""
    findings = []
    if not DB_INSTRUMENTS.exists():
        return findings

    db = json.loads(DB_INSTRUMENTS.read_text())
    for inst in db.get("instruments", []):
        if not inst.get("has_memory", False):
            continue  # Semi-modulars with no patch memory don't need param files
        slug = inst["slug"]
        param_file = MIDI_PARAMS_DIR / f"{slug}.json"
        if param_file.exists():
            findings.append({
                "check": "midi_params",
                "slug": slug,
                "status": "pass",
                "detail": f"database/midi_params/{slug}.json present",
            })
        else:
            findings.append({
                "check": "midi_params",
                "slug": slug,
                "status": "warn",
                "detail": f"No database/midi_params/{slug}.json — consider adding MIDI CC map",
            })
    return findings


def check_skill_references() -> list[dict]:
    """Check that files referenced inside SKILL.md files actually exist."""
    findings = []
    if not SKILLS_DIR.exists():
        findings.append({
            "check": "skill_references",
            "skill": "_all",
            "status": "warn",
            "detail": ".github/skills/ directory not found",
        })
        return findings

    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        skill_name = skill_md.parent.name
        content = skill_md.read_text()
        # Look for file paths in backtick spans that look like repo paths
        import re
        candidates = re.findall(r"`([a-zA-Z0-9_./\-]+\.[a-zA-Z]{2,5})`", content)
        broken = []
        for c in candidates:
            if "/" in c and not c.startswith("http"):
                target = REPO_ROOT / c
                if not target.exists():
                    broken.append(c)
        if broken:
            findings.append({
                "check": "skill_references",
                "skill": skill_name,
                "status": "warn",
                "detail": f"References to missing files: {broken}",
            })
        else:
            findings.append({
                "check": "skill_references",
                "skill": skill_name,
                "status": "pass",
                "detail": "All detected file references exist",
            })
    return findings


def check_active_song() -> list[dict]:
    """Verify songs.json exists and has exactly one active song (or zero with a warning)."""
    findings = []
    if not DB_SONGS.exists():
        findings.append({
            "check": "active_song",
            "status": "fail",
            "detail": "database/songs.json does not exist",
        })
        return findings

    db = json.loads(DB_SONGS.read_text())
    active = [s for s in db.get("songs", []) if s.get("status") == "active"]
    if len(active) == 1:
        findings.append({
            "check": "active_song",
            "status": "pass",
            "detail": f"Active song: {active[0]['slug']} ({active[0]['title']})",
        })
    elif len(active) == 0:
        findings.append({
            "check": "active_song",
            "status": "warn",
            "detail": "No active song — Copilot will ask before generating key-specific content",
        })
    else:
        slugs = [s["slug"] for s in active]
        findings.append({
            "check": "active_song",
            "status": "fail",
            "detail": f"Multiple active songs found: {slugs} — only one should be active",
        })
    return findings


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_health_json(findings: list[dict], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for f in findings:
        counts[f.get("status", "fail")] += 1

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": counts,
        "findings": findings,
    }
    out_file = out_dir / "repo_health.json"
    out_file.write_text(json.dumps(payload, indent=2))
    log.info("Wrote %s", out_file)
    return out_file


def write_issues_md(findings: list[dict], out_dir: Path) -> Path | None:
    problems = [f for f in findings if f.get("status") in ("fail", "warn")]
    if not problems:
        # Remove stale issues file if everything is clean
        stale = out_dir / "repo_health_issues.md"
        if stale.exists():
            stale.unlink()
        return None

    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Repo Health Issues — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "",
        f"Found **{len(problems)}** issue(s) requiring attention.",
        "",
    ]

    by_check: dict[str, list[dict]] = {}
    for f in problems:
        key = f.get("check", "unknown")
        by_check.setdefault(key, []).append(f)

    check_titles = {
        "instrument_folders": "Instrument Folder Structure",
        "instruments_registered": "Instrument Registration",
        "midi_params": "MIDI Parameter Files",
        "skill_references": "Skill File References",
        "active_song": "Active Song",
    }

    for check_key, items in by_check.items():
        lines.append(f"## {check_titles.get(check_key, check_key)}")
        lines.append("")
        for item in items:
            icon = "🔴" if item["status"] == "fail" else "🟡"
            label = item.get("slug") or item.get("skill") or ""
            lines.append(f"- {icon} **{label}**: {item['detail']}")
        lines.append("")

    out_file = out_dir / "repo_health_issues.md"
    out_file.write_text("\n".join(lines))
    log.info("Wrote %s", out_file)
    return out_file


def maybe_generate_suggestions(findings: list[dict]) -> str | None:
    """Use Gemini to explain issues and suggest fixes if GEMINI_API_KEY is available."""
    if not os.environ.get("GEMINI_API_KEY"):
        log.info("GEMINI_API_KEY not set — skipping AI suggestions")
        return None

    problems = [f for f in findings if f.get("status") == "fail"]
    if not problems:
        return None

    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from llm_utils import complete

        problem_text = "\n".join(
            f"- [{f['check']}] {f.get('slug', f.get('skill', ''))} — {f['detail']}"
            for f in problems
        )
        prompt = (
            "You are the machine half of IRON STATIC, an electronic metal duo. "
            "The following issues were found during the weekly repo health audit:\n\n"
            f"{problem_text}\n\n"
            "For each issue, give a one-line concrete fix command or action the human collaborator "
            "(Dave Arnold) can take immediately to resolve it. Be direct and hardware-specific "
            "where applicable. Use the IRON STATIC instrument slugs (digitakt, rev2, take5, etc)."
        )
        return complete(prompt, model_tier="fast")
    except Exception as exc:
        log.warning("Gemini call failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="IRON STATIC repo health audit")
    parser.add_argument(
        "--out-dir",
        default=str(OUTPUTS_DIR),
        help="Directory to write outputs/repo_health.json and repo_health_issues.md",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip Gemini AI suggestions even if GEMINI_API_KEY is set",
    )
    args = parser.parse_args()
    out_dir = Path(args.out_dir)

    log.info("Running IRON STATIC repo health audit from %s", REPO_ROOT)

    findings: list[dict] = []
    findings += check_instrument_folders()
    findings += check_instruments_registered()
    findings += check_midi_params()
    findings += check_skill_references()
    findings += check_active_song()

    health_file = write_health_json(findings, out_dir)
    issues_file = write_issues_md(findings, out_dir)

    fail_count = sum(1 for f in findings if f["status"] == "fail")
    warn_count = sum(1 for f in findings if f["status"] == "warn")
    pass_count = sum(1 for f in findings if f["status"] == "pass")

    log.info("Results: %d pass, %d warn, %d fail", pass_count, warn_count, fail_count)

    if not args.no_llm and fail_count > 0:
        suggestions = maybe_generate_suggestions(findings)
        if suggestions and issues_file:
            with open(issues_file, "a") as f:
                f.write("\n## AI Suggestions\n\n")
                f.write(suggestions)
                f.write("\n")
            log.info("Appended AI suggestions to %s", issues_file)

    # Exit non-zero only on hard failures so CI can optionally gate on this
    return 1 if fail_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
