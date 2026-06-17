#!/usr/bin/env bash
# sync-to-rhoai.sh — Phase 7: Sync stable → rhoai with .tekton/.github removal.
# Usage: sync-to-rhoai.sh [VERSION]
set -euo pipefail

VERSION="${1:-}"
STABLE_BRANCH="stable"
FORK_REMOTE="${FORK_REMOTE:-origin}"

# Determine RHOAI branch from state or environment
RHOAI_VERSION="${RHOAI_VERSION:-}"
if [[ -z "$RHOAI_VERSION" ]]; then
  echo "ERROR: RHOAI_VERSION not set. Export it or pass via state." >&2
  exit 2
fi

RHOAI_BRANCH="rhoai-${RHOAI_VERSION}"
PR_BRANCH="sync-rhoai-${RHOAI_VERSION}"

echo "=== Phase 7: Sync Stable → RHOAI (${RHOAI_BRANCH}) ==="
echo "Source: midstream/${STABLE_BRANCH}"
echo "Target: midstream/${RHOAI_BRANCH}"
echo ""

# Fetch latest
git fetch midstream "${STABLE_BRANCH}" "${RHOAI_BRANCH}" 2>/dev/null

# Create PR branch from rhoai
git switch -c "${PR_BRANCH}" "midstream/${RHOAI_BRANCH}" 2>/dev/null || {
  echo "ERROR: Cannot create branch from midstream/${RHOAI_BRANCH}" >&2
  exit 1
}

# Merge stable content with theirs strategy
if ! git merge "midstream/${STABLE_BRANCH}" --no-commit --strategy=recursive --strategy-option=theirs 2>/dev/null; then
  git checkout --theirs -- . 2>/dev/null || true
  git add -A
fi

# Remove .tekton/ and .github/workflows/ (not needed on rhoai branch)
if [[ -d ".tekton" ]]; then
  git rm -rf .tekton 2>/dev/null || true
  echo "Removed .tekton/ from rhoai branch"
fi
if [[ -d ".github/workflows" ]]; then
  git rm -rf .github/workflows 2>/dev/null || true
  echo "Removed .github/workflows/ from rhoai branch"
fi

git add -A

COMMIT_MSG="Sync stable to rhoai (OVMS ${VERSION:-${RHOAI_VERSION}})"
git commit -m "$COMMIT_MSG" --allow-empty

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
  --base "${RHOAI_BRANCH}" \
  --title "Sync stable to ${RHOAI_BRANCH}" \
  --body "Sync stable branch content to ${RHOAI_BRANCH}.

.tekton/ and .github/workflows/ removed (not applicable to rhoai branch)." \
  2>/dev/null)

echo ""
echo "PR created: ${PR_URL}"
echo "PR_URL=${PR_URL}"
