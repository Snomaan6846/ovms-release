#!/usr/bin/env bash
# check-prerequisites.sh — Tool/auth gate ONLY.
# Verifies required tools are installed and gh is authenticated.
# Exit 0 = all OK, Exit 1 = missing prerequisite.
set -euo pipefail

ERRORS=0

check_tool() {
  local tool="$1"
  local required="${2:-true}"
  if command -v "$tool" &>/dev/null; then
    echo -e "[OK]\t${tool}"
  elif [[ "$required" == "true" ]]; then
    echo -e "[FAIL]\t${tool} — not found" >&2
    ERRORS=$((ERRORS + 1))
  else
    echo -e "[INFO]\t${tool} — not installed (optional)"
  fi
}

echo "=== Tool Check ==="
check_tool git
check_tool gh
check_tool python3
check_tool jq
check_tool patch
check_tool skopeo false

# E2E tools — graceful skip if not needed
E2E_ENABLED="${E2E_ENABLED:-false}"
if [[ "$E2E_ENABLED" == "true" ]]; then
  if command -v podman &>/dev/null || command -v docker &>/dev/null; then
    echo -e "[OK]\tpodman/docker"
  else
    echo -e "[FAIL]\tpodman or docker — required for E2E phases" >&2
    ERRORS=$((ERRORS + 1))
  fi
  check_tool oc
else
  if command -v podman &>/dev/null || command -v docker &>/dev/null; then
    echo -e "[OK]\tpodman/docker (available for E2E)"
  else
    echo -e "[INFO]\tpodman/docker — not installed (E2E phases will be skipped)"
  fi
  if command -v oc &>/dev/null; then
    echo -e "[OK]\toc (available for E2E)"
  else
    echo -e "[INFO]\toc — not installed (E2E phases will be skipped)"
  fi
fi

echo ""
echo "=== Authentication Check ==="

if gh auth status &>/dev/null 2>&1; then
  echo -e "[OK]\tgh authenticated"
else
  echo -e "[FAIL]\tgh not authenticated — run: gh auth login" >&2
  ERRORS=$((ERRORS + 1))
fi

echo ""
echo "=== Git Remotes Check ==="

FORK_REMOTE="${FORK_REMOTE:-origin}"
MIDSTREAM_REMOTE="${MIDSTREAM_REMOTE:-midstream}"
DOWNSTREAM_REMOTE="${DOWNSTREAM_REMOTE:-downstream}"

for remote in "$FORK_REMOTE" "$MIDSTREAM_REMOTE" "$DOWNSTREAM_REMOTE"; do
  if git remote get-url "$remote" &>/dev/null 2>&1; then
    echo -e "[OK]\tremote '${remote}' configured"
  else
    echo -e "[WARN]\tremote '${remote}' not configured"
  fi
done

echo ""
echo "=== Jira Backend Detection (informational) ==="

if command -v acli &>/dev/null; then
  if acli jira auth status &>/dev/null 2>&1; then
    echo -e "[OK]\tJira: acli authenticated"
  else
    echo -e "[INFO]\tJira: acli installed but not authenticated (run: acli jira auth)"
  fi
elif [[ -n "${JIRA_API_TOKEN:-}" && -n "${JIRA_USER_EMAIL:-}" ]]; then
  echo -e "[OK]\tJira: REST API credentials configured"
else
  echo -e "[INFO]\tJira: not configured (release tracking will be state-file only)"
fi

echo ""
echo "=== Notification Check (informational) ==="

if [[ -n "${NOTIFICATION_WEBHOOK:-}" ]]; then
  echo -e "[OK]\tNotifications: webhook configured"
else
  echo -e "[INFO]\tNotifications: no webhook configured (silent mode)"
fi

echo ""
if [[ $ERRORS -gt 0 ]]; then
  echo "FAILED: ${ERRORS} prerequisite(s) missing." >&2
  exit 1
fi
echo "All prerequisites satisfied."
exit 0
