#!/usr/bin/env bash
# IRON STATIC Bridge — 06_gcs_push
set -euo pipefail
cd "$(dirname "$0")/../../"
python scripts/gcs_sync.py --push
