#!/usr/bin/env python3
"""
GCS large-file sync for IRON STATIC.

Commands:
  push <path> [<path>...]  Upload file(s) or a directory to GCS, update manifest
  pull <gcs_path>          Download a single file from GCS to its repo-relative path
  ls [--prefix P]          List files tracked in the manifest
  status [--prefix P]      Compare local files against the manifest
  index [--prefix P]       Rebuild manifest by listing the live GCS bucket

Auth:
  Local  — gcloud ADC: run `gcloud auth application-default login`
  CI     — set GCS_SA_KEY env var to the full service account JSON key string
  Both   — set GCS_BUCKET env var or use --bucket flag

Secrets needed in GitHub Actions:
  GCS_SA_KEY  — service account JSON key (full JSON string, not a path)
  GCS_BUCKET  — bucket name (e.g. iron-static-files)
"""

import argparse
import hashlib
import json
import logging
import mimetypes
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_PATH = Path(__file__).parent.parent / "database" / "gcs_manifest.json"
REPO_ROOT = Path(__file__).parent.parent

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GCS client
# ---------------------------------------------------------------------------

def get_client():
    """Return an authenticated google.cloud.storage.Client.

    In CI set GCS_SA_KEY to the full service account JSON string.
    Locally, gcloud ADC is used (no env var needed).
    The key is parsed directly in memory — never written to disk.
    """
    try:
        from google.cloud import storage
    except ImportError:
        log.error("google-cloud-storage not installed. Run: pip install google-cloud-storage")
        sys.exit(1)

    sa_key_json = os.environ.get("GCS_SA_KEY")
    if sa_key_json:
        from google.oauth2 import service_account
        try:
            info = json.loads(sa_key_json)
        except json.JSONDecodeError as exc:
            log.error("GCS_SA_KEY is not valid JSON: %s", exc)
            sys.exit(1)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        return storage.Client(credentials=creds, project=info.get("project_id"))

    # Application Default Credentials (local dev)
    return storage.Client()


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {"bucket": "", "last_updated": "", "files": {}}


def save_manifest(manifest: dict) -> None:
    manifest["last_updated"] = datetime.now(timezone.utc).isoformat()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    log.info("Manifest saved: %s", MANIFEST_PATH.relative_to(REPO_ROOT))


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_relative(path: Path) -> str:
    """Return repo-relative POSIX string for a path."""
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def bucket_name(manifest: dict, args) -> str:
    name = getattr(args, "bucket", None) or os.environ.get("GCS_BUCKET") or manifest.get("bucket")
    if not name:
        log.error(
            "No bucket specified. Use --bucket, the GCS_BUCKET env var, "
            "or push once with --bucket to record it in the manifest."
        )
        sys.exit(1)
    return name


def human_size(n: int) -> str:
    for unit in ("B", "K", "M", "G"):
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.1f}T"


# ---------------------------------------------------------------------------
# push
# ---------------------------------------------------------------------------

def cmd_push(args):
    manifest = load_manifest()
    bkt_name = bucket_name(manifest, args)
    manifest["bucket"] = bkt_name

    # Collect paths
    paths = []
    for raw in args.paths:
        p = Path(raw)
        if p.is_dir():
            log.info("Scanning directory: %s", p)
            paths.extend(f for f in sorted(p.rglob("*")) if f.is_file())
        elif p.is_file():
            paths.append(p)
        else:
            log.warning("Path not found, skipping: %s", raw)

    if not paths:
        log.error("No files to push.")
        sys.exit(1)

    client = None if args.dry_run else get_client()
    bucket = None if args.dry_run else client.bucket(bkt_name)
    pushed = skipped = 0

    for local in paths:
        gcs_key = repo_relative(local)
        size = local.stat().st_size
        checksum = sha256_file(local)
        content_type = mimetypes.guess_type(str(local))[0] or "application/octet-stream"

        existing = manifest["files"].get(gcs_key)
        if existing and existing.get("sha256") == checksum and not args.force:
            log.info("  skip (unchanged): %s", gcs_key)
            skipped += 1
            continue

        if args.dry_run:
            log.info("  [dry-run] push: %s  (%s)", gcs_key, human_size(size))
            pushed += 1
            continue

        log.info("  push: %s  (%s)", gcs_key, human_size(size))
        blob = bucket.blob(gcs_key)
        blob.upload_from_filename(str(local), content_type=content_type)
        pushed += 1

        manifest["files"][gcs_key] = {
            "size_bytes": size,
            "sha256": checksum,
            "content_type": content_type,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "tags": list(args.tag) if args.tag else [],
        }

    log.info("Pushed %d file(s), skipped %d unchanged.", pushed, skipped)
    if not args.dry_run:
        save_manifest(manifest)


# ---------------------------------------------------------------------------
# pull
# ---------------------------------------------------------------------------

def cmd_pull(args):
    manifest = load_manifest()
    bkt_name = bucket_name(manifest, args)

    gcs_key = args.gcs_path
    dest = Path(args.dest) if args.dest else (REPO_ROOT / gcs_key)

    if args.dry_run:
        log.info("[dry-run] pull: gs://%s/%s → %s", bkt_name, gcs_key, dest)
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    log.info("Pulling: gs://%s/%s → %s", bkt_name, gcs_key, dest)
    client = get_client()
    blob = client.bucket(bkt_name).blob(gcs_key)
    blob.download_to_filename(str(dest))
    log.info("  done  (%s)", human_size(dest.stat().st_size))


# ---------------------------------------------------------------------------
# ls
# ---------------------------------------------------------------------------

def cmd_ls(args):
    manifest = load_manifest()
    files = manifest.get("files", {})
    prefix = args.prefix or ""
    tag_filter = args.tag

    results = {
        k: v for k, v in files.items()
        if k.startswith(prefix)
        and (not tag_filter or tag_filter in v.get("tags", []))
    }

    if args.json:
        print(json.dumps(results, indent=2))
        return

    if not results:
        print("(no files match)")
        return

    bucket = manifest.get("bucket", "?")
    w = min(max((len(k) for k in results), default=0), 70)
    print(f"{'path':<{w}}  {'size':>8}  {'uploaded_at':>20}  tags")
    print("-" * (w + 40))
    total_bytes = 0
    for key in sorted(results):
        meta = results[key]
        size = meta.get("size_bytes", 0)
        total_bytes += size
        ts = meta.get("uploaded_at", "")[:19].replace("T", " ")
        tags = ", ".join(meta.get("tags", []))
        print(f"{key:<{w}}  {human_size(size):>8}  {ts:>20}  {tags}")

    print(f"\n{len(results)} file(s)  {human_size(total_bytes)} total  gs://{bucket}/")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def cmd_status(args):
    manifest = load_manifest()
    files = manifest.get("files", {})
    prefix = args.prefix or ""

    tracked = {k: v for k, v in files.items() if k.startswith(prefix)}

    in_sync, modified, missing_local, untracked = [], [], [], []

    for gcs_key, meta in tracked.items():
        local = REPO_ROOT / gcs_key
        if not local.exists():
            missing_local.append(gcs_key)
        elif sha256_file(local) == meta.get("sha256"):
            in_sync.append(gcs_key)
        else:
            modified.append(gcs_key)

    # Scan local untracked files if a prefix directory exists
    scan_dir = REPO_ROOT / prefix if prefix else None
    if scan_dir and scan_dir.is_dir():
        for local in sorted(scan_dir.rglob("*")):
            if local.is_file():
                rel = repo_relative(local)
                if rel not in files:
                    untracked.append(rel)

    if in_sync:
        print(f"  in-sync ({len(in_sync)}):")
        for f in sorted(in_sync):
            print(f"    = {f}")

    if modified:
        print(f"\n  modified — local differs from GCS ({len(modified)}):")
        for f in sorted(modified):
            print(f"    M {f}")

    if missing_local:
        print(f"\n  in GCS but not on disk ({len(missing_local)}):")
        for f in sorted(missing_local):
            print(f"    - {f}")

    if untracked:
        shown = sorted(untracked)[:25]
        print(f"\n  local only, not in GCS ({len(untracked)}):")
        for f in shown:
            print(f"    + {f}")
        if len(untracked) > 25:
            print(f"    ... and {len(untracked) - 25} more")

    if not any([in_sync, modified, missing_local, untracked]):
        print("  (no files tracked or found under this prefix)")


# ---------------------------------------------------------------------------
# index  — rebuild manifest from live bucket
# ---------------------------------------------------------------------------

def cmd_index(args):
    manifest = load_manifest()
    bkt_name = bucket_name(manifest, args)
    manifest["bucket"] = bkt_name

    prefix = args.prefix or ""
    log.info("Listing gs://%s/%s ...", bkt_name, prefix)

    client = get_client()
    blobs = list(client.list_blobs(bkt_name, prefix=prefix or None))
    log.info("  found %d blob(s)", len(blobs))

    for blob in blobs:
        key = blob.name
        meta = manifest["files"].get(key, {})
        meta.update({
            "size_bytes": blob.size,
            "content_type": blob.content_type or "application/octet-stream",
            "uploaded_at": blob.updated.isoformat() if blob.updated else "",
        })
        if not meta.get("sha256"):
            # GCS md5 is base64; store it as a fallback until a real sha256 is computed
            meta["sha256"] = ""
        meta.setdefault("tags", [])
        manifest["files"][key] = meta

    if args.dry_run:
        log.info("[dry-run] would write manifest with %d file(s)", len(manifest["files"]))
    else:
        save_manifest(manifest)
        log.info("Manifest rebuilt: %d file(s)", len(manifest["files"]))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="GCS large-file sync for IRON STATIC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--bucket",
        metavar="NAME",
        help="GCS bucket name (overrides GCS_BUCKET env var and manifest value)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- push ---
    p_push = sub.add_parser("push", help="Upload file(s) to GCS and update manifest")
    p_push.add_argument("paths", nargs="+", help="Local file(s) or directory to upload")
    p_push.add_argument("--tag", action="append", metavar="TAG", help="Tag label (repeatable)")
    p_push.add_argument("--force", action="store_true", help="Re-upload even if SHA256 matches")
    p_push.add_argument("--dry-run", action="store_true")

    # --- pull ---
    p_pull = sub.add_parser("pull", help="Download a file from GCS")
    p_pull.add_argument("gcs_path", help="GCS key (e.g. audio/recordings/raw/foo.wav)")
    p_pull.add_argument("--dest", metavar="PATH", help="Local destination (default: mirrors GCS key under repo root)")
    p_pull.add_argument("--dry-run", action="store_true")

    # --- ls ---
    p_ls = sub.add_parser("ls", help="List files tracked in the manifest")
    p_ls.add_argument("--prefix", metavar="P", help="Filter by GCS path prefix")
    p_ls.add_argument("--tag", metavar="TAG", help="Filter by tag")
    p_ls.add_argument("--json", action="store_true", help="Output as JSON")

    # --- status ---
    p_status = sub.add_parser("status", help="Compare local files against GCS manifest")
    p_status.add_argument("--prefix", metavar="P", help="Scope to a path prefix")

    # --- index ---
    p_index = sub.add_parser("index", help="Rebuild manifest by listing the live GCS bucket")
    p_index.add_argument("--prefix", metavar="P", help="Only list blobs with this prefix")
    p_index.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    {
        "push": cmd_push,
        "pull": cmd_pull,
        "ls": cmd_ls,
        "status": cmd_status,
        "index": cmd_index,
    }[args.command](args)


if __name__ == "__main__":
    main()
