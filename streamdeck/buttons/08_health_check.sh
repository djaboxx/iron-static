#!/usr/bin/env bash
# IRON STATIC Bridge — 08_health_check
set -euo pipefail
cd "$(dirname "$0")/../../"
python scripts/run_repo_health.py
