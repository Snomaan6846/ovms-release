#!/usr/bin/env bash
# preflight.sh — Phase 0: Full intelligence gathering.
# Calls check-prerequisites.sh first, then gathers upstream state, diffs, PyPI versions, UBI tags.
# Usage: preflight.sh [VERSION]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="${1:-}"

# Step 1: Check prerequisites
echo "=== Running prerequisite checks ==="
bash "${SCRIPT_DIR}/check-prerequisites.sh" || exit 1
echo ""

# Step 2: Detect upstream releases if no version specified
if [[ -z "$VERSION" ]]; then
  echo "=== Detecting upstream releases ==="
  bash "${SCRIPT_DIR}/detect-upstream-releases.sh"
  echo ""
  echo "Specify a version to continue: preflight.sh <VERSION>"
  exit 0
fi

# Parse version
YEAR="${VERSION%%.*}"
MINOR="${VERSION#*.}"
UPSTREAM_BRANCH="releases/${YEAR}/${MINOR}"
MIDSTREAM_BRANCH="${YEAR}.${MINOR}-release"

echo "=== Release Brief for OVMS ${VERSION} ==="
echo ""

# Step 3: Check upstream branch existence
echo "--- Upstream Status ---"
for repo in model_server openvino openvino.genai openvino_tokenizers; do
  if gh api "repos/openvinotoolkit/${repo}/branches/${UPSTREAM_BRANCH}" --jq .name &>/dev/null 2>&1; then
    echo -e "[OK]\topenvinotoolkit/${repo} — branch '${UPSTREAM_BRANCH}' exists"
  else
    echo -e "[MISS]\topenvinotoolkit/${repo} — branch '${UPSTREAM_BRANCH}' NOT FOUND"
  fi
done
echo ""

# Step 4: Check midstream branch state
echo "--- Midstream Status ---"
if gh api "repos/opendatahub-io/openvino_model_server/branches/${MIDSTREAM_BRANCH}" --jq .name &>/dev/null 2>&1; then
  echo -e "[EXISTS]\topendatahub-io/openvino_model_server/${MIDSTREAM_BRANCH} — already mirrored"
else
  echo -e "[NEW]\topendatahub-io/openvino_model_server/${MIDSTREAM_BRANCH} — needs creation"
fi
echo ""

# Step 5: ARG diff (if previous release branch exists)
echo "--- Dockerfile ARG Changes ---"
PREV_MINOR=$((MINOR - 1))
PREV_VERSION="${YEAR}.${PREV_MINOR}"
PREV_BRANCH="${YEAR}.${PREV_MINOR}-release"

if git show "midstream/${PREV_BRANCH}:Dockerfile.redhat" &>/dev/null 2>&1 && \
   git show "midstream/${MIDSTREAM_BRANCH}:Dockerfile.redhat" &>/dev/null 2>&1; then
  bash "${SCRIPT_DIR}/diff-args.sh" "${PREV_VERSION}" "${VERSION}" 2>/dev/null || echo "(ARG diff unavailable — branches not fetched locally)"
else
  echo "(ARG diff unavailable — fetch midstream branches first)"
fi
echo ""

# Step 6: Patch health check (git apply --check)
echo "--- Patches Branch Health ---"
if git ls-remote midstream patches &>/dev/null 2>&1; then
  git fetch midstream patches --depth=1 2>/dev/null || true
  if git ls-tree --name-only midstream/patches &>/dev/null 2>&1; then
    for patch in $(git ls-tree --name-only midstream/patches 2>/dev/null); do
      if git show "midstream/patches:${patch}" 2>/dev/null | git apply --check - &>/dev/null 2>&1; then
        echo -e "  ${patch}\tOK (applies cleanly)"
      else
        echo -e "  ${patch}\tFAILED"
      fi
    done
  else
    echo "  (patches branch empty or not fetchable)"
  fi
else
  echo "  (patches branch not found on midstream remote)"
fi
echo ""

# Step 7: Python dep versions (PyPI check)
echo "--- Python Dependencies ---"
if command -v python3 &>/dev/null; then
  python3 "${SCRIPT_DIR}/check-pypi-versions.py" 2>/dev/null || echo "  (PyPI check failed)"
else
  echo "  (python3 not available)"
fi
echo ""

# Step 8: Fork sync warning
echo "--- Fork Health ---"
FORK_BEHIND=$(git rev-list "origin/main..midstream/main" --count 2>/dev/null || echo "unknown")
if [[ "$FORK_BEHIND" == "0" ]]; then
  echo -e "[OK]\tFork is up to date with midstream"
elif [[ "$FORK_BEHIND" == "unknown" ]]; then
  echo -e "[INFO]\tCannot determine fork divergence (fetch remotes first)"
else
  echo -e "[WARN]\tFork is ${FORK_BEHIND} commits behind midstream/main"
  echo -e "\tRun: git fetch midstream && git push origin midstream/main:main"
fi
echo ""

echo "=== End Release Brief ==="
echo ""
echo "Ready to proceed? Run: ovms-release mirror ${VERSION}"
