#!/usr/bin/env bash
# push-owners.sh — Phase 2: Add OWNERS file to openvino_model_server release branch via PR.
# Usage: push-owners.sh <VERSION>
set -euo pipefail

VERSION="${1:?Usage: push-owners.sh <VERSION>}"
YEAR="${VERSION%%.*}"
MINOR="${VERSION#*.}"
MIDSTREAM_BRANCH="${YEAR}.${MINOR}-release"
FORK_REMOTE="${FORK_REMOTE:-origin}"
PR_BRANCH="add-owners-${VERSION}"

echo "=== Phase 2: Push OWNERS (OVMS ${VERSION}) ==="

# Create branch from midstream release branch
git fetch midstream "${MIDSTREAM_BRANCH}" 2>/dev/null
git switch -c "${PR_BRANCH}" "midstream/${MIDSTREAM_BRANCH}" 2>/dev/null || \
  git switch "${PR_BRANCH}" 2>/dev/null

# Create OWNERS file if it doesn't exist or needs updating
cat > OWNERS << 'EOF'
approvers:
  - opendatahub-io/odh-model-runtimes

reviewers:
  - opendatahub-io/odh-model-runtimes
EOF

git add OWNERS
if git diff --cached --quiet; then
  echo "OWNERS file already up to date — skipping."
  git switch -
  git branch -D "${PR_BRANCH}" 2>/dev/null || true
  exit 0
fi

git commit -m "Add OWNERS file for ${VERSION} release branch"

if [[ "${DRY_RUN:-}" == "1" ]]; then
  echo "[DRY RUN] Would push ${PR_BRANCH} and create PR"
  git switch -
  git branch -D "${PR_BRANCH}" 2>/dev/null || true
  exit 0
fi

git push -u "${FORK_REMOTE}" "${PR_BRANCH}"

PR_URL=$(gh pr create \
  --repo "opendatahub-io/openvino_model_server" \
  --base "${MIDSTREAM_BRANCH}" \
  --title "Add OWNERS to ${MIDSTREAM_BRANCH}" \
  --body "Add OWNERS file for the ${VERSION} release branch." \
  2>/dev/null)

echo "PR created: ${PR_URL}"
echo ""
echo "PR_URL=${PR_URL}"
