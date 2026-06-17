#!/usr/bin/env bash
# generate-release-notes.sh — Generate release notes from state + git log.
# Usage: generate-release-notes.sh [VERSION]
set -euo pipefail

VERSION="${1:-}"

# Load state to get version info
if [[ -z "$VERSION" ]]; then
  STATE_DIR="${HOME}/.ovms-release/openvino_model_server"
  if [[ -d "$STATE_DIR" ]]; then
    LATEST=$(ls -t "$STATE_DIR" 2>/dev/null | head -1)
    VERSION="${LATEST}"
  fi
fi

if [[ -z "$VERSION" ]]; then
  echo "ERROR: No version specified and no active release found." >&2
  exit 1
fi

YEAR="${VERSION%%.*}"
MINOR="${VERSION#*.}"
MIDSTREAM_BRANCH="${YEAR}.${MINOR}-release"

echo "# OVMS ${VERSION} Release Notes"
echo ""
echo "## Release Information"
echo ""
echo "- **Version**: ${VERSION}"
echo "- **Upstream branch**: releases/${YEAR}/${MINOR}"
echo "- **Midstream branch**: ${MIDSTREAM_BRANCH}"
echo "- **Date**: $(date -u +%Y-%m-%d)"
echo ""

# Commit summary from upstream
echo "## Changes from Upstream"
echo ""
PREV_MINOR=$((MINOR - 1))
PREV_BRANCH="${YEAR}.${PREV_MINOR}-release"

if git log "midstream/${PREV_BRANCH}..midstream/${MIDSTREAM_BRANCH}" --oneline 2>/dev/null | head -20; then
  :
else
  echo "(Unable to determine commit delta — fetch branches first)"
fi
echo ""

# ARG changes
echo "## Build Configuration Changes"
echo ""
if [[ -f "$(dirname "$0")/diff-args.sh" ]]; then
  bash "$(dirname "$0")/diff-args.sh" "${VERSION}" 2>/dev/null || echo "(ARG diff unavailable)"
fi
echo ""

# Known issues / patches
echo "## Patches Applied"
echo ""
PATCHES=$(git ls-tree --name-only midstream/patches 2>/dev/null | sort || true)
if [[ -n "$PATCHES" ]]; then
  echo "$PATCHES" | while read -r p; do
    echo "- ${p}"
  done
else
  echo "(No patches)"
fi
echo ""

echo "## Verification"
echo ""
echo "- [ ] ODH image builds successfully"
echo "- [ ] E2E tests pass"
echo "- [ ] RHDS sync complete"
echo "- [ ] quay.io image available"
