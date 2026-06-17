#!/usr/bin/env bash
# save-state.sh — Atomic write to release-state.yaml.
# Usage: save-state.sh <VERSION> <FIELD_PATH> <VALUE>
# Example: save-state.sh 2026.2 phases.mirror_branches.status completed
set -euo pipefail

VERSION="${1:?Usage: save-state.sh <VERSION> <FIELD_PATH> <VALUE>}"
FIELD_PATH="${2:?Missing field path}"
VALUE="${3:?Missing value}"

STATE_DIR="${HOME}/.ovms-release/openvino_model_server/${VERSION}"
STATE_FILE="${STATE_DIR}/release-state.yaml"

if [[ ! -f "$STATE_FILE" ]]; then
  echo "ERROR: State file not found: ${STATE_FILE}" >&2
  exit 1
fi

# Use python for safe YAML manipulation
python3 -c "
import yaml
from pathlib import Path

state_file = Path('${STATE_FILE}')
with open(state_file) as f:
    state = yaml.safe_load(f)

# Navigate the field path
parts = '${FIELD_PATH}'.split('.')
obj = state
for part in parts[:-1]:
    if part not in obj:
        obj[part] = {}
    obj = obj[part]

# Set the value (handle booleans and numbers)
value = '${VALUE}'
if value.lower() == 'true':
    obj[parts[-1]] = True
elif value.lower() == 'false':
    obj[parts[-1]] = False
elif value.isdigit():
    obj[parts[-1]] = int(value)
else:
    obj[parts[-1]] = value

# Atomic write
tmp = state_file.with_suffix('.yaml.tmp')
with open(tmp, 'w') as f:
    yaml.dump(state, f, default_flow_style=False, sort_keys=False)
tmp.rename(state_file)
print(f'Updated {\".\".join(parts)} = {value}')
"
