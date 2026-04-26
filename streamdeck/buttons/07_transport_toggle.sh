#!/usr/bin/env bash
# IRON STATIC Bridge — 07_transport_toggle
set -euo pipefail
cd "$(dirname "$0")/../../"
python scripts/bridge_client.py transport_toggle
