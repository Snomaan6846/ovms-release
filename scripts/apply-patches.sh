#!/usr/bin/env bash
# apply-patches.sh — Phase 5: Fetch patches, apply, detect conflicts.
# Usage: apply-patches.sh <VERSION>
set -euo pipefail

VERSION="${1:?Usage: apply-patches.sh <VERSION>}"
YEAR="${VERSION%%.*}"
MINOR="${VERSION#*.}"
MIDSTREAM_BRANCH="${YEAR}.${MINOR}-release"
FORK_REMOTE="${FORK_REMOTE:-origin}"
PR_BRANCH="apply-patches-${VERSION}"

echo "=== Phase 5: Apply Patches (OVMS ${VERSION}) ==="

# Fetch patches branch
git fetch midstream patches --depth=1 2>/dev/null
git fetch midstream "${MIDSTREAM_BRANCH}" 2>/dev/null

# Create working branch from release branch
git switch -c "${PR_BRANCH}" "midstream/${MIDSTREAM_BRANCH}" 2>/dev/null || {
  echo "ERROR: Cannot create branch from midstream/${MIDSTREAM_BRANCH}" >&2
  exit 1
}

# Get list of patches in order
PATCHES=$(git ls-tree --name-only midstream/patches 2>/dev/null | sort)
if [[ -z "$PATCHES" ]]; then
  echo "ERROR: No patches found on midstream/patches branch" >&2
  git switch -
  git branch -D "${PR_BRANCH}" 2>/dev/null || true
  exit 1
fi

echo "Patches to apply:"
echo "$PATCHES" | sed 's/^/  /'
echo ""

# Apply patches 01-03 (pre-Dockerfile.konflux)
FAILED=0
for patch in $(echo "$PATCHES" | grep -v '^04-'); do
  echo -n "Applying ${patch}... "
  if git show "midstream/patches:${patch}" | git apply - 2>/dev/null; then
    echo "OK"
    git add -A
  else
    echo "FAILED"
    FAILED=$((FAILED + 1))
    echo "  Conflict detected in ${patch}. Manual resolution needed." >&2
  fi
done

# Create Dockerfile.konflux from Dockerfile.redhat
if [[ -f "Dockerfile.redhat" ]]; then
  cp Dockerfile.redhat Dockerfile.konflux
  git add Dockerfile.konflux
  echo "Created Dockerfile.konflux from Dockerfile.redhat"
fi

# Apply patch 04 (label patch targeting Dockerfile.konflux)
LABEL_PATCH=$(echo "$PATCHES" | grep '^04-' || true)
if [[ -n "$LABEL_PATCH" ]]; then
  echo -n "Applying ${LABEL_PATCH}... "
  if git show "midstream/patches:${LABEL_PATCH}" | git apply - 2>/dev/null; then
    echo "OK"
    git add -A
  else
    echo "FAILED"
    FAILED=$((FAILED + 1))
  fi
fi

if [[ $FAILED -gt 0 ]]; then
  echo ""
  echo "ERROR: ${FAILED} patch(es) failed to apply." >&2
  echo "Resolve conflicts manually, then commit and push." >&2
  exit 1
fi

# Commit all changes
git commit -m "Apply release patches for OVMS ${VERSION}

Patches applied:
$(echo "$PATCHES" | sed 's/^/- /')"

if [[ "${DRY_RUN:-}" == "1" ]]; then
  echo ""
  echo "[DRY RUN] Would push and create PR"
  git switch -
  git branch -D "${PR_BRANCH}" 2>/dev/null || true
  exit 0
fi

# Push and create PR
git push -u "${FORK_REMOTE}" "${PR_BRANCH}"

PR_URL=$(gh pr create \
  --repo "opendatahub-io/openvino_model_server" \
  --base "${MIDSTREAM_BRANCH}" \
  --title "Apply release patches for ${VERSION}" \
  --body "Applied patches from the patches branch for OVMS ${VERSION} release." \
  2>/dev/null)

echo ""
echo "PR created: ${PR_URL}"
echo "PR_URL=${PR_URL}"
