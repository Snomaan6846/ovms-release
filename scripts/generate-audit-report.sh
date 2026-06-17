#!/usr/bin/env bash
# generate-audit-report.sh — Produce compliance/audit report from release state.
# Usage: generate-audit-report.sh [VERSION]
set -euo pipefail

VERSION="${1:-}"

STATE_DIR="${HOME}/.ovms-release/openvino_model_server"
if [[ -z "$VERSION" ]]; then
  LATEST=$(ls -t "$STATE_DIR" 2>/dev/null | head -1)
  VERSION="${LATEST}"
fi

STATE_FILE="${STATE_DIR}/${VERSION}/release-state.yaml"

if [[ ! -f "$STATE_FILE" ]]; then
  echo "ERROR: State file not found: ${STATE_FILE}" >&2
  exit 1
fi

echo "# OVMS ${VERSION} Release Audit Report"
echo ""
echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# Parse state via Python
python3 -c "
import yaml
from pathlib import Path

state = yaml.safe_load(Path('${STATE_FILE}').read_text())
config = state.get('config', {})
phases = state.get('phases', {})
pr_urls = state.get('pr_urls', {})

print('## Release Metadata')
print(f\"- Status: {state.get('status', 'unknown')}\")
print(f\"- Started: {state.get('started_at', 'unknown')}\")
print(f\"- Started by: {state.get('started_by', 'unknown')}\")
if state.get('aborted_at'):
    print(f\"- Aborted: {state.get('aborted_at')}\")
    print(f\"- Abort reason: {state.get('abort_reason')}\")
print()

print('## Configuration')
print(f\"- Upstream: {config.get('upstream_org', '?')}\")
print(f\"- Midstream: {config.get('midstream_org', '?')}\")
print(f\"- Downstream: {config.get('downstream_org', '?')}\")
print(f\"- RHOAI version: {config.get('rhoai_version', 'not set')}\")
print(f\"- Jira ticket: {config.get('jira_ticket_url', 'none')}\")
print()

print('## Phase Status')
print('| Phase | Status | Notes |')
print('|-------|--------|-------|')
for phase_name, phase_data in phases.items():
    status = phase_data.get('status', '?')
    notes = phase_data.get('notes', '')[:50]
    print(f\"| {phase_name} | {status} | {notes} |\")
print()

print('## Pull Requests')
for name, url in pr_urls.items():
    status_icon = '✓' if url else '—'
    print(f\"- {name}: {url or '(not created)'} {status_icon}\")
print()

print('## Security Checklist')
print('- [ ] No credentials stored in state file')
print('- [ ] All changes via PR (no direct push)')
print('- [ ] PR approvals obtained before merge')
print('- [ ] Protected files preserved in tree transplant')
print('- [ ] Base image from approved registry')
"
