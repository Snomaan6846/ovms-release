#!/usr/bin/env bash
# check-image-labels.sh — Phase 5.5: Verify OCI image labels match expectations.
# Usage: check-image-labels.sh <IMAGE_URL>
set -euo pipefail

IMAGE="${1:?Usage: check-image-labels.sh <IMAGE_URL>}"

echo "=== Image Label Verification: ${IMAGE} ==="
echo ""

if ! command -v skopeo &>/dev/null; then
  echo "[SKIP] skopeo not installed — cannot verify labels" >&2
  exit 0
fi

# Inspect image
LABELS=$(skopeo inspect "docker://${IMAGE}" 2>/dev/null | jq -r '.Labels // empty')

if [[ -z "$LABELS" || "$LABELS" == "null" ]]; then
  echo "[FAIL] Cannot inspect image or no labels found" >&2
  exit 1
fi

echo "Labels found:"
echo "$LABELS" | jq -r 'to_entries[] | "  \(.key) = \(.value)"'
echo ""

# Verify required labels
ERRORS=0
check_label() {
  local key="$1"
  local value
  value=$(echo "$LABELS" | jq -r --arg k "$key" '.[$k] // empty')
  if [[ -n "$value" ]]; then
    echo -e "[OK]\t${key} = ${value}"
  else
    echo -e "[MISS]\t${key} — not set" >&2
    ERRORS=$((ERRORS + 1))
  fi
}

echo "--- Required Labels ---"
check_label "com.redhat.component"
check_label "name"
check_label "version"
check_label "summary"
check_label "description"
check_label "io.openshift.tags"
check_label "io.k8s.display-name"
check_label "io.k8s.description"

echo ""
echo "--- Konflux Labels ---"
check_label "build-date"
check_label "vcs-ref"
check_label "vcs-type"

echo ""
if [[ $ERRORS -gt 0 ]]; then
  echo "WARNING: ${ERRORS} label(s) missing."
  exit 1
fi
echo "All required labels present."
