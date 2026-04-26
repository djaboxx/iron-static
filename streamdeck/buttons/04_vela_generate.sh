#!/usr/bin/env bash
# IRON STATIC Bridge — 04_vela_generate
set -euo pipefail
cd "$(dirname "$0")/../../"
python scripts/gemini_forge.py --element vocal
