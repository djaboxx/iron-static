#!/usr/bin/env bash
# IRON STATIC Bridge — 02_git_commit
set -euo pipefail
cd "$(dirname "$0")/../../"
python scripts/run_session_summarizer.py
