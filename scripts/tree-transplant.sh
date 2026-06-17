#!/usr/bin/env bash
# tree-transplant.sh — Phase 6: Tree transplant merge (release → stable).
# Exit 0=success, 1=git-failure, 2=user-review-required (untracked files need cleanup).
# Usage: tree-transplant.sh <VERSION> [--confirm-clean]
set -euo pipefail

VERSION="${1:?Usage: tree-transplant.sh <VERSION> [--confirm-clean]}"
CONFIRM_CLEAN="${2:-}"

YEAR="${VERSION%%.*}"
MINOR="${VERSION#*.}"
MIDSTREAM_BRANCH="${YEAR}.${MINOR}-release"
STABLE_BRANCH="stable"
FORK_REMOTE="${FORK_REMOTE:-origin}"
PR_BRANCH="sync-stable-${VERSION}"

echo "=== Phase 6: Tree Transplant Merge (OVMS ${VERSION}) ==="
echo "Source: midstream/${MIDSTREAM_BRANCH}"
echo "Target: midstream/${STABLE_BRANCH}"
echo ""

# Fetch latest
git fetch midstream "${MIDSTREAM_BRANCH}" "${STABLE_BRANCH}" 2>/dev/null

# Create PR branch from stable
git switch -c "${PR_BRANCH}" "midstream/${STABLE_BRANCH}" 2>/dev/null || {
  echo "ERROR: Cannot create branch from midstream/${STABLE_BRANCH}" >&2
  exit 1
}

# Step 1: Record protected files before merge
TEKTON_FILES=$(git ls-tree -r --name-only HEAD .tekton/ 2>/dev/null || true)
GH_WORKFLOW_FILES=$(git ls-tree -r --name-only HEAD .github/workflows/ 2>/dev/null || true)

# Step 2: Perform merge with strategy=theirs for file content (tree transplant)
MERGE_BASE=$(git merge-base HEAD "midstream/${MIDSTREAM_BRANCH}")
echo "Merge base: ${MERGE_BASE:0:8}"

if ! git merge "midstream/${MIDSTREAM_BRANCH}" --no-commit --strategy=recursive --strategy-option=theirs 2>/dev/null; then
  echo "Merge conflicts detected. Resolving with theirs strategy..."
  git checkout --theirs -- . 2>/dev/null || true
  git add -A
fi

# Step 3: Restore protected files from stable
echo "Restoring protected files..."
if [[ -n "$TEKTON_FILES" ]]; then
  echo "$TEKTON_FILES" | while read -r f; do
    git checkout "midstream/${STABLE_BRANCH}" -- "$f" 2>/dev/null || true
  done
fi
if [[ -n "$GH_WORKFLOW_FILES" ]]; then
  echo "$GH_WORKFLOW_FILES" | while read -r f; do
    git checkout "midstream/${STABLE_BRANCH}" -- "$f" 2>/dev/null || true
  done
fi

# Step 4: Check for untracked files that need cleanup
UNTRACKED=$(git clean -n -d 2>/dev/null | grep -v '.tekton/' | grep -v '.github/workflows/' || true)
if [[ -n "$UNTRACKED" && "$CONFIRM_CLEAN" != "--confirm-clean" ]]; then
  echo ""
  echo "WARNING: Untracked files detected after merge:"
  echo "$UNTRACKED"
  echo ""
  echo "Re-run with --confirm-clean to remove these files."
  exit 2
fi

if [[ -n "$UNTRACKED" && "$CONFIRM_CLEAN" == "--confirm-clean" ]]; then
  git clean -fd 2>/dev/null || true
fi

# Step 5: Commit
git add -A
git commit -m "Sync ${VERSION} content to stable (OVMS ${VERSION})

Tree transplant merge from ${MIDSTREAM_BRANCH} to stable.
Protected files (.tekton/, .github/workflows/) preserved from stable."

if [[ "${DRY_RUN:-}" == "1" ]]; then
  echo ""
  echo "[DRY RUN] Would push and create PR"
  git switch -
  git branch -D "${PR_BRANCH}" 2>/dev/null || true
  exit 0
fi

# Step 6: Push and create PR
git push -u "${FORK_REMOTE}" "${PR_BRANCH}"

PR_URL=$(gh pr create \
  --repo "opendatahub-io/openvino_model_server" \
  --base "${STABLE_BRANCH}" \
  --title "Sync ${VERSION} to stable" \
  --body "Tree transplant merge of ${MIDSTREAM_BRANCH} content to stable branch.

Protected files (.tekton/, .github/workflows/) preserved from stable." \
  2>/dev/null)

echo ""
echo "PR created: ${PR_URL}"
echo "PR_URL=${PR_URL}"
exit 0
