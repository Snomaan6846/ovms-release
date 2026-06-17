#!/usr/bin/env bash
# check-pr-status.sh — Check PR merge status via gh API.
# Usage: check-pr-status.sh <PR_URL>
# Exit 0 = merged, Exit 1 = open, Exit 2 = closed (not merged), Exit 3 = error
set -euo pipefail

PR_URL="${1:?Usage: check-pr-status.sh <PR_URL>}"

# Extract org/repo and PR number from URL
# e.g., https://github.com/opendatahub-io/openvino_model_server/pull/123
REPO=$(echo "$PR_URL" | sed -E 's|https://github.com/([^/]+/[^/]+)/pull/.*|\1|')
PR_NUM=$(echo "$PR_URL" | sed -E 's|.*/pull/([0-9]+).*|\1|')

if [[ -z "$REPO" || -z "$PR_NUM" ]]; then
  echo "ERROR: Cannot parse PR URL: ${PR_URL}" >&2
  exit 3
fi

STATE=$(gh pr view "$PR_NUM" --repo "$REPO" --json state,merged --jq '.state + "\t" + (.merged | tostring)' 2>/dev/null)

if [[ -z "$STATE" ]]; then
  echo "ERROR: Cannot fetch PR status" >&2
  exit 3
fi

PR_STATE=$(echo "$STATE" | cut -f1)
PR_MERGED=$(echo "$STATE" | cut -f2)

case "$PR_STATE" in
  MERGED)
    echo "MERGED"
    exit 0
    ;;
  OPEN)
    echo "OPEN"
    exit 1
    ;;
  CLOSED)
    if [[ "$PR_MERGED" == "true" ]]; then
      echo "MERGED"
      exit 0
    fi
    echo "CLOSED"
    exit 2
    ;;
  *)
    echo "UNKNOWN: ${PR_STATE}"
    exit 3
    ;;
esac
