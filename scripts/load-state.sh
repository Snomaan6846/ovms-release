#!/usr/bin/env bash
# load-state.sh — Read and parse release-state.yaml.
# Usage: load-state.sh [VERSION]
# Outputs key=value pairs for shell consumption (eval-safe).
set -euo pipefail

VERSION="${1:-}"
STATE_DIR="${HOME}/.ovms-release/openvino_model_server"

if [[ -n "$VERSION" ]]; then
  STATE_FILE="${STATE_DIR}/${VERSION}/release-state.yaml"
else
  # Find most recent state file
  STATE_FILE=""
  if [[ -d "$STATE_DIR" ]]; then
    STATE_FILE=$(find "$STATE_DIR" -name "release-state.yaml" -printf '%T@ %p\n' 2>/dev/null \
      | sort -rn | head -1 | cut -d' ' -f2)
  fi
fi

if [[ -z "$STATE_FILE" || ! -f "$STATE_FILE" ]]; then
  echo "ERROR: No state file found" >&2
  exit 1
fi

echo "STATE_FILE=${STATE_FILE}"
echo "STATE_VERSION=$(python3 -c "import yaml; d=yaml.safe_load(open('${STATE_FILE}')); print(f\"{d.get('config',{}).get('year','')}.{d.get('config',{}).get('minor','')}\") " 2>/dev/null || echo "unknown")"
echo "STATE_STATUS=$(python3 -c "import yaml; print(yaml.safe_load(open('${STATE_FILE}')).get('status','unknown'))" 2>/dev/null || echo "unknown")"
