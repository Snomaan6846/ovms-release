#!/usr/bin/env bash
# diff-args.sh — Phase 3: ARG diff between old/new Dockerfile.redhat.
# Usage: diff-args.sh <OLD_VERSION> <NEW_VERSION>
#   or:  diff-args.sh <VERSION>  (compares against previous minor)
set -euo pipefail

if [[ $# -eq 2 ]]; then
  OLD_VERSION="$1"
  NEW_VERSION="$2"
elif [[ $# -eq 1 ]]; then
  NEW_VERSION="$1"
  YEAR="${NEW_VERSION%%.*}"
  MINOR="${NEW_VERSION#*.}"
  PREV_MINOR=$((MINOR - 1))
  OLD_VERSION="${YEAR}.${PREV_MINOR}"
else
  echo "Usage: diff-args.sh <OLD_VERSION> <NEW_VERSION>" >&2
  exit 2
fi

OLD_YEAR="${OLD_VERSION%%.*}"
OLD_MINOR="${OLD_VERSION#*.}"
NEW_YEAR="${NEW_VERSION%%.*}"
NEW_MINOR="${NEW_VERSION#*.}"

OLD_BRANCH="${OLD_YEAR}.${OLD_MINOR}-release"
NEW_BRANCH="${NEW_YEAR}.${NEW_MINOR}-release"

extract_args() {
  local branch="$1"
  # Extract ARG lines from Dockerfile.redhat on the given branch
  git show "midstream/${branch}:Dockerfile.redhat" 2>/dev/null \
    | grep -E '^ARG ' \
    | sed 's/^ARG //' \
    | sort
}

echo "=== Dockerfile ARG Diff: ${OLD_VERSION} → ${NEW_VERSION} ==="
echo ""

OLD_ARGS=$(extract_args "$OLD_BRANCH")
NEW_ARGS=$(extract_args "$NEW_BRANCH")

if [[ -z "$OLD_ARGS" ]]; then
  echo "ERROR: Could not read Dockerfile.redhat from midstream/${OLD_BRANCH}" >&2
  echo "  Ensure 'git fetch midstream ${OLD_BRANCH}' has been run." >&2
  exit 1
fi

if [[ -z "$NEW_ARGS" ]]; then
  echo "ERROR: Could not read Dockerfile.redhat from midstream/${NEW_BRANCH}" >&2
  echo "  Ensure 'git fetch midstream ${NEW_BRANCH}' has been run." >&2
  exit 1
fi

# Compare ARG names (key=value -> key)
OLD_KEYS=$(echo "$OLD_ARGS" | cut -d= -f1 | sort)
NEW_KEYS=$(echo "$NEW_ARGS" | cut -d= -f1 | sort)

# NEW args (in new but not old)
ADDED=$(comm -13 <(echo "$OLD_KEYS") <(echo "$NEW_KEYS"))
if [[ -n "$ADDED" ]]; then
  echo "NEW:"
  while read -r key; do
    val=$(echo "$NEW_ARGS" | grep "^${key}=" | cut -d= -f2-)
    echo -e "  ${key}=${val}"
  done <<< "$ADDED"
  echo ""
fi

# REMOVED args (in old but not new)
REMOVED=$(comm -23 <(echo "$OLD_KEYS") <(echo "$NEW_KEYS"))
if [[ -n "$REMOVED" ]]; then
  echo "REMOVED:"
  while read -r key; do
    val=$(echo "$OLD_ARGS" | grep "^${key}=" | cut -d= -f2-)
    echo -e "  ${key}=${val}"
  done <<< "$REMOVED"
  echo ""
fi

# CHANGED args (same key, different value)
COMMON=$(comm -12 <(echo "$OLD_KEYS") <(echo "$NEW_KEYS"))
CHANGED=""
while read -r key; do
  [[ -z "$key" ]] && continue
  old_val=$(echo "$OLD_ARGS" | grep "^${key}=" | cut -d= -f2-)
  new_val=$(echo "$NEW_ARGS" | grep "^${key}=" | cut -d= -f2-)
  if [[ "$old_val" != "$new_val" ]]; then
    CHANGED="${CHANGED}  ${key}: ${old_val} → ${new_val}\n"
  fi
done <<< "$COMMON"

if [[ -n "$CHANGED" ]]; then
  echo "CHANGED:"
  echo -e "$CHANGED"
fi

if [[ -z "$ADDED" && -z "$REMOVED" && -z "$CHANGED" ]]; then
  echo "No ARG changes between ${OLD_VERSION} and ${NEW_VERSION}."
fi
