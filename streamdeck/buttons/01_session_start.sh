#!/usr/bin/env bash
# IRON STATIC Bridge — 01_session_start
set -euo pipefail
cd "$(dirname "$0")/../../"
python scripts/manage_songs.py list
