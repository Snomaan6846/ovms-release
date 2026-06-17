#!/usr/bin/env bash
# check-rhds-sync.sh — Phase 8: Check RHDS auto-sync + quay.io image availability.
# Usage: check-rhds-sync.sh <VERSION>
set -euo pipefail

VERSION="${1:?Usage: check-rhds-sync.sh <VERSION>}"
RHOAI_VERSION="${RHOAI_VERSION:-}"

echo "=== Phase 8: RHDS Sync Verification (OVMS ${VERSION}) ==="

if [[ -z "$RHOAI_VERSION" ]]; then
  echo "ERROR: RHOAI_VERSION not set." >&2
  exit 2
fi

# Check if RHDS branch exists and has the sync
RHDS_BRANCH="rhoai-${RHOAI_VERSION}"
echo "Checking red-hat-data-services/openvino_model_server branch: ${RHDS_BRANCH}"

if gh api "repos/red-hat-data-services/openvino_model_server/branches/${RHDS_BRANCH}" --jq .name &>/dev/null 2>&1; then
  echo -e "[OK]\tRHDS branch '${RHDS_BRANCH}' exists"
else
  echo -e "[PENDING]\tRHDS branch '${RHDS_BRANCH}' not yet created (auto-sync may be pending)"
fi

# Check quay.io image
IMAGE="quay.io/rhoai/odh-openvino-model-server-rhel9:rhoai-${RHOAI_VERSION}"
echo ""
echo "Checking image: ${IMAGE}"

if command -v skopeo &>/dev/null; then
  if skopeo inspect "docker://${IMAGE}" &>/dev/null 2>&1; then
    DIGEST=$(skopeo inspect "docker://${IMAGE}" 2>/dev/null | jq -r '.Digest' || echo "unknown")
    echo -e "[OK]\tImage available (digest: ${DIGEST})"
    echo ""
    echo "FINAL_IMAGE=${IMAGE}"
    echo "FINAL_DIGEST=${DIGEST}"
  else
    echo -e "[PENDING]\tImage not yet available"
  fi
else
  # Fallback: use curl to check quay.io API
  TAGS=$(curl -sf "https://quay.io/api/v1/repository/rhoai/odh-openvino-model-server-rhel9/tag/?limit=10" \
    | jq -r '.tags[].name' 2>/dev/null || echo "")
  if echo "$TAGS" | grep -q "rhoai-${RHOAI_VERSION}"; then
    echo -e "[OK]\tImage tag found on quay.io"
  else
    echo -e "[PENDING]\tImage tag not yet available"
  fi
fi
