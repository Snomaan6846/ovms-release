#!/usr/bin/env bash
# verify-sync.sh — Phase 6 post-step: Verify tree transplant (Check A + B + C).
# Called SEPARATELY by SKILL.md after tree-transplant.sh succeeds.
# Usage: verify-sync.sh <VERSION>
set -euo pipefail

VERSION="${1:?Usage: verify-sync.sh <VERSION>}"
YEAR="${VERSION%%.*}"
MINOR="${VERSION#*.}"
MIDSTREAM_BRANCH="${YEAR}.${MINOR}-release"
STABLE_BRANCH="stable"

echo "=== Verification Checks for ${VERSION} stable sync ==="
ERRORS=0

# Check A: File content matches release branch (excluding protected files)
echo ""
echo "--- Check A: Content matches release branch ---"
DIFF_OUTPUT=$(git diff --name-only "midstream/${MIDSTREAM_BRANCH}" "midstream/${STABLE_BRANCH}" -- \
  ':!.tekton' ':!.github/workflows' 2>/dev/null || echo "DIFF_ERROR")

if [[ "$DIFF_OUTPUT" == "DIFF_ERROR" ]]; then
  echo "[FAIL] Cannot compare branches (fetch them first)"
  ERRORS=$((ERRORS + 1))
elif [[ -z "$DIFF_OUTPUT" ]]; then
  echo "[OK] All non-protected files match release branch"
else
  echo "[FAIL] Files differ between release and stable (excluding .tekton/.github/workflows):"
  echo "$DIFF_OUTPUT" | head -20 | sed 's/^/  /'
  ERRORS=$((ERRORS + 1))
fi

# Check B: .tekton/ and .github/workflows/ preserved from stable
echo ""
echo "--- Check B: Protected files preserved ---"

TEKTON_COUNT=$(git ls-tree -r --name-only "midstream/${STABLE_BRANCH}" .tekton/ 2>/dev/null | wc -l)
if [[ "$TEKTON_COUNT" -gt 0 ]]; then
  echo "[OK] .tekton/ directory present (${TEKTON_COUNT} files)"
else
  echo "[WARN] .tekton/ directory empty or missing"
fi

GH_COUNT=$(git ls-tree -r --name-only "midstream/${STABLE_BRANCH}" .github/workflows/ 2>/dev/null | wc -l)
if [[ "$GH_COUNT" -gt 0 ]]; then
  echo "[OK] .github/workflows/ present (${GH_COUNT} files)"
else
  echo "[WARN] .github/workflows/ empty or missing"
fi

# Check C: WORKSPACE file not modified by tree transplant (Bazel integrity)
echo ""
echo "--- Check C: WORKSPACE integrity ---"
if git show "midstream/${STABLE_BRANCH}:WORKSPACE" &>/dev/null 2>&1; then
  RELEASE_WS=$(git show "midstream/${MIDSTREAM_BRANCH}:WORKSPACE" 2>/dev/null | sha256sum | cut -d' ' -f1)
  STABLE_WS=$(git show "midstream/${STABLE_BRANCH}:WORKSPACE" 2>/dev/null | sha256sum | cut -d' ' -f1)
  if [[ "$RELEASE_WS" == "$STABLE_WS" ]]; then
    echo "[OK] WORKSPACE file matches release branch"
  else
    echo "[WARN] WORKSPACE file differs — verify Bazel build still works"
  fi
else
  echo "[OK] No WORKSPACE file (non-Bazel project)"
fi

echo ""
if [[ $ERRORS -gt 0 ]]; then
  echo "VERIFICATION FAILED: ${ERRORS} check(s) did not pass."
  exit 1
fi
echo "All verification checks passed."
exit 0
