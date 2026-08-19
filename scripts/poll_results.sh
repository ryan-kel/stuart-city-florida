#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

python3 "$SCRIPT_DIR/fetch_clarity.py"
python3 "$SCRIPT_DIR/build_map.py"

DEPLOY_DATA_DIR="${EA_STUART_DEPLOY_DATA:-}"
if [[ -n "$DEPLOY_DATA_DIR" && -d "$DEPLOY_DATA_DIR" ]]; then
  install -m 0644 "$PROJECT_DIR/data/map_data.json" "$DEPLOY_DATA_DIR/map_data.json"
  echo "Synced poll data to $DEPLOY_DATA_DIR"
fi
