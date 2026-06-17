#!/usr/bin/env bash
# mirror-branches.sh — Phase 1: Create mirror branches in 4 ODH repos.
# Uses repo-specific branch naming (openvino_model_server differs from helpers).
# Usage: mirror-branches.sh <VERSION> [--validate]
set -euo pipefail

VERSION="${1:?Usage: mirror-branches.sh <VERSION> [--validate]}"
VALIDATE_ONLY="${2:-}"

YEAR="${VERSION%%.*}"
MINOR="${VERSION#*.}"
UPSTREAM_BRANCH="releases/${YEAR}/${MINOR}"

declare -A REPO_MAP=(
  ["model_server"]="openvino_model_server"
  ["openvino"]="openvino"
  ["openvino.genai"]="openvino.genai"
  ["openvino_tokenizers"]="openvino_tokenizers"
)

get_midstream_branch() {
  local repo="$1"
  if [[ "$repo" == "openvino_model_server" ]]; then
    echo "${YEAR}.${MINOR}-release"
  else
    echo "${UPSTREAM_BRANCH}"
  fi
}

echo "=== Phase 1: Mirror Branches (OVMS ${VERSION}) ==="
ERRORS=0

for upstream_repo in model_server openvino openvino.genai openvino_tokenizers; do
  midstream_repo="${REPO_MAP[$upstream_repo]}"
  midstream_branch=$(get_midstream_branch "$midstream_repo")

  # Validate upstream exists
  UPSTREAM_SHA=$(gh api "repos/openvinotoolkit/${upstream_repo}/git/ref/heads/${UPSTREAM_BRANCH}" \
    --jq '.object.sha' 2>/dev/null || echo "")

  if [[ -z "$UPSTREAM_SHA" ]]; then
    echo -e "[FAIL]\topenvinotoolkit/${upstream_repo}: upstream branch '${UPSTREAM_BRANCH}' not found"
    ERRORS=$((ERRORS + 1))
    continue
  fi

  echo -e "[OK]\topenvinotoolkit/${upstream_repo}: ${UPSTREAM_BRANCH} @ ${UPSTREAM_SHA:0:8}"

  if [[ "$VALIDATE_ONLY" == "--validate" ]]; then
    continue
  fi

  # Check if midstream branch already exists
  EXISTING=$(gh api "repos/opendatahub-io/${midstream_repo}/git/ref/heads/${midstream_branch}" \
    --jq '.object.sha' 2>/dev/null || echo "")

  if [[ -n "$EXISTING" ]]; then
    echo -e "\t→ midstream branch '${midstream_branch}' already exists (${EXISTING:0:8})"
    continue
  fi

  # Create midstream branch
  if [[ "${DRY_RUN:-}" == "1" ]]; then
    echo -e "\t→ [DRY RUN] Would create opendatahub-io/${midstream_repo}:${midstream_branch} from ${UPSTREAM_SHA:0:8}"
    echo -e "\t→ [DRY RUN] Would tag mirror-point/${VERSION}/${midstream_repo}"
  else
    gh api "repos/opendatahub-io/${midstream_repo}/git/refs" \
      -f "ref=refs/heads/${midstream_branch}" \
      -f "sha=${UPSTREAM_SHA}" &>/dev/null \
      && echo -e "\t→ Created opendatahub-io/${midstream_repo}:${midstream_branch}" \
      || { echo -e "\t→ [FAIL] Could not create branch"; ERRORS=$((ERRORS + 1)); continue; }

    # Tag the mirror point for auditability
    gh api "repos/opendatahub-io/${midstream_repo}/git/refs" \
      -f "ref=refs/tags/mirror-point/${VERSION}" \
      -f "sha=${UPSTREAM_SHA}" &>/dev/null \
      && echo -e "\t→ Tagged mirror-point/${VERSION}" \
      || echo -e "\t→ [WARN] Could not create mirror point tag"
  fi
done

if [[ $ERRORS -gt 0 ]]; then
  echo ""
  echo "ERRORS: ${ERRORS} repo(s) failed."
  exit 1
fi

echo ""
echo "All branches mirrored successfully."
exit 0
