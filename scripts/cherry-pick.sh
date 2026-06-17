#!/usr/bin/env bash
# cherry-pick.sh — Cherry-pick flow for hotfixes to older releases.
# Usage: cherry-pick.sh <COMMIT_SHA> <TARGET_BRANCH>
set -euo pipefail

SHA="${1:?Usage: cherry-pick.sh <COMMIT_SHA> <TARGET_BRANCH>}"
TARGET_BRANCH="${2:?Usage: cherry-pick.sh <COMMIT_SHA> <TARGET_BRANCH>}"
FORK_REMOTE="${FORK_REMOTE:-origin}"

echo "=== Cherry-pick ${SHA:0:8} → ${TARGET_BRANCH} ==="

# Determine target repo based on branch name
if [[ "$TARGET_BRANCH" == rhoai-* ]]; then
  TARGET_REPO="red-hat-data-services/openvino_model_server"
  REMOTE="downstream"
else
  TARGET_REPO="opendatahub-io/openvino_model_server"
  REMOTE="midstream"
fi

echo "Target: ${TARGET_REPO} / ${TARGET_BRANCH}"

# Validate commit exists
if ! git show --oneline "${SHA}" &>/dev/null 2>&1; then
  echo "ERROR: Commit ${SHA} not found locally. Run: git fetch --all" >&2
  exit 1
fi

# Fetch target branch
git fetch "${REMOTE}" "${TARGET_BRANCH}" 2>/dev/null

# Check if already an ancestor
if git merge-base --is-ancestor "${SHA}" "${REMOTE}/${TARGET_BRANCH}" 2>/dev/null; then
  echo "Commit is already on ${TARGET_BRANCH} — nothing to do."
  exit 0
fi

# Create branch
PR_BRANCH="cp-${SHA:0:8}-to-${TARGET_BRANCH}"
git switch -c "${PR_BRANCH}" "${REMOTE}/${TARGET_BRANCH}" 2>/dev/null

# Cherry-pick
if git cherry-pick -x "${SHA}" 2>/dev/null; then
  echo "Cherry-pick applied cleanly."
else
  echo "CONFLICT during cherry-pick. Resolve manually, then:"
  echo "  git add . && git cherry-pick --continue"
  echo "  git push -u ${FORK_REMOTE} ${PR_BRANCH}"
  exit 1
fi

if [[ "${DRY_RUN:-}" == "1" ]]; then
  echo "[DRY RUN] Would push and create PR"
  git switch -
  git branch -D "${PR_BRANCH}" 2>/dev/null || true
  exit 0
fi

# Push and create PR
git push -u "${FORK_REMOTE}" "${PR_BRANCH}"

PR_URL=$(gh pr create \
  --repo "${TARGET_REPO}" \
  --base "${TARGET_BRANCH}" \
  --title "Cherry-pick ${SHA:0:8} to ${TARGET_BRANCH}" \
  --body "Cherry-pick of ${SHA} for hotfix." \
  2>/dev/null)

echo "PR created: ${PR_URL}"
