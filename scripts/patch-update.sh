#!/usr/bin/env bash
# patch-update.sh — Diagnose patch failures, validate regenerated patches.
# Usage: patch-update.sh <VERSION>
set -euo pipefail

VERSION="${1:?Usage: patch-update.sh <VERSION>}"
YEAR="${VERSION%%.*}"
MINOR="${VERSION#*.}"
MIDSTREAM_BRANCH="${YEAR}.${MINOR}-release"

echo "=== Patch Update Diagnosis (OVMS ${VERSION}) ==="

# Fetch patches and release branch
git fetch midstream patches --depth=1 2>/dev/null
git fetch midstream "${MIDSTREAM_BRANCH}" --depth=1 2>/dev/null

echo ""
echo "--- Patch Health Report ---"

PATCHES=$(git ls-tree --name-only midstream/patches 2>/dev/null | sort)
FAILED_PATCHES=""

for patch in $PATCHES; do
  if git show "midstream/patches:${patch}" 2>/dev/null | \
     git apply --check --directory=. - &>/dev/null 2>&1; then
    echo -e "  ${patch}\tOK"
  else
    ERROR=$(git show "midstream/patches:${patch}" 2>/dev/null | \
            git apply --check --directory=. - 2>&1 | head -1 || echo "unknown error")
    echo -e "  ${patch}\tFAILED (${ERROR})"
    FAILED_PATCHES="${FAILED_PATCHES} ${patch}"
  fi
done

if [[ -z "$FAILED_PATCHES" ]]; then
  echo ""
  echo "All patches apply cleanly. No update needed."
  exit 0
fi

echo ""
echo "Failed patches:${FAILED_PATCHES}"
echo ""
echo "To regenerate, create fixes on a temporary branch and use:"
echo "  git diff HEAD -- <file> > /tmp/regenerated-<patch-name>"
echo ""
echo "Then validate with: patch-update.sh ${VERSION} --validate"
