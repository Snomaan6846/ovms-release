#!/usr/bin/env bash
# detect-upstream-releases.sh — Query upstream for available releases not yet mirrored.
# Compares upstream branch list against midstream to find new releases.
set -euo pipefail

echo "Checking upstream releases..."

# Get upstream release branches (model_server uses 'releases/YEAR/MINOR')
UPSTREAM=$(gh api repos/openvinotoolkit/model_server/branches --paginate --jq '.[].name' 2>/dev/null \
  | grep '^releases/' | sort)

# Get midstream branches and convert naming to upstream format
MIRRORED=$(gh api repos/opendatahub-io/openvino_model_server/branches --paginate --jq '.[].name' 2>/dev/null \
  | grep -- '-release$' \
  | sed 's/\(.*\)\.\(.*\)-release/releases\/\1\/\2/' | sort)

# Find releases not yet mirrored
NEW=$(comm -23 <(echo "$UPSTREAM") <(echo "$MIRRORED") 2>/dev/null || true)

if [[ -n "$NEW" ]]; then
  echo ""
  echo "New upstream releases available (not yet mirrored to ODH):"
  echo "$NEW" | while read -r branch; do
    version=$(echo "$branch" | sed 's|releases/\(.*\)/\(.*\)|\1.\2|')
    echo "  ${version}  (upstream branch: ${branch})"
  done
  echo ""
  echo "To start a release: /ovms-release <version>"
else
  echo ""
  echo "All upstream releases are already mirrored."
  echo ""
  echo "Currently mirrored:"
  echo "$MIRRORED" | while read -r branch; do
    version=$(echo "$branch" | sed 's|releases/\(.*\)/\(.*\)|\1.\2|')
    echo "  ${version}"
  done
fi
