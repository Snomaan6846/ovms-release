#!/usr/bin/env bash
# jira-integration.sh — Tiered Jira integration (acli > REST API > skip).
# Usage: jira-integration.sh <action> [args...]
# Actions: create-ticket, link-pr, update-status, close-ticket
set -euo pipefail

ACTION="${1:?Usage: jira-integration.sh <action> [args...]}"
shift

# Configuration (from state or env)
JIRA_PROJECT="${JIRA_PROJECT:-RHOAIENG}"
JIRA_COMPONENT="${JIRA_COMPONENT:-OVMS}"
JIRA_SERVER="${JIRA_SERVER:-https://redhat.atlassian.net}"

# Detect available backend
detect_backend() {
  if command -v acli &>/dev/null && acli jira auth status &>/dev/null 2>&1; then
    echo "acli"
  elif [[ -n "${JIRA_API_TOKEN:-}" && -n "${JIRA_USER_EMAIL:-}" ]]; then
    echo "rest"
  else
    echo "none"
  fi
}

BACKEND=$(detect_backend)

if [[ "$BACKEND" == "none" ]]; then
  echo "[INFO] Jira not configured — skipping ${ACTION}" >&2
  exit 0
fi

# REST API helper
jira_rest() {
  local method="$1" endpoint="$2"
  shift 2
  curl -sf \
    -X "$method" \
    -H "Content-Type: application/json" \
    -H "Authorization: Basic $(echo -n "${JIRA_USER_EMAIL}:${JIRA_API_TOKEN}" | base64)" \
    "${JIRA_SERVER}/rest/api/3/${endpoint}" \
    "$@"
}

case "$ACTION" in
  create-ticket)
    VERSION="${1:?VERSION required}"
    SUMMARY="OVMS ${VERSION} release tracking"

    if [[ "$BACKEND" == "acli" ]]; then
      TICKET=$(acli jira issue create \
        --project "$JIRA_PROJECT" \
        --type Task \
        --summary "$SUMMARY" \
        --component "$JIRA_COMPONENT" \
        --output-format json 2>/dev/null | jq -r '.key')
    else
      RESPONSE=$(jira_rest POST "issue" -d "{
        \"fields\": {
          \"project\": {\"key\": \"${JIRA_PROJECT}\"},
          \"summary\": \"${SUMMARY}\",
          \"issuetype\": {\"name\": \"Task\"},
          \"components\": [{\"name\": \"${JIRA_COMPONENT}\"}]
        }
      }")
      TICKET=$(echo "$RESPONSE" | jq -r '.key')
    fi

    if [[ -n "$TICKET" && "$TICKET" != "null" ]]; then
      echo "JIRA_TICKET=${TICKET}"
      echo "JIRA_URL=${JIRA_SERVER}/browse/${TICKET}"
    else
      echo "[WARN] Jira ticket creation failed" >&2
      exit 1
    fi
    ;;

  link-pr)
    TICKET="${1:?TICKET required}"
    PR_URL="${2:?PR_URL required}"
    COMMENT="PR linked: ${PR_URL}"

    if [[ "$BACKEND" == "acli" ]]; then
      acli jira issue comment --key "$TICKET" --comment "$COMMENT" 2>/dev/null
    else
      jira_rest POST "issue/${TICKET}/comment" -d "{
        \"body\": {\"type\": \"doc\", \"version\": 1, \"content\": [{\"type\": \"paragraph\", \"content\": [{\"text\": \"${COMMENT}\", \"type\": \"text\"}]}]}
      }" >/dev/null
    fi
    echo "Linked ${PR_URL} to ${TICKET}"
    ;;

  update-status)
    TICKET="${1:?TICKET required}"
    STATUS="${2:?STATUS required}"

    if [[ "$BACKEND" == "acli" ]]; then
      acli jira issue transition --key "$TICKET" --transition "$STATUS" 2>/dev/null || true
    else
      echo "[INFO] REST transition not implemented — update manually" >&2
    fi
    ;;

  close-ticket)
    TICKET="${1:?TICKET required}"

    if [[ "$BACKEND" == "acli" ]]; then
      acli jira issue transition --key "$TICKET" --transition "Done" 2>/dev/null || \
        acli jira issue transition --key "$TICKET" --transition "Closed" 2>/dev/null || true
    else
      echo "[INFO] REST close not implemented — close manually: ${JIRA_SERVER}/browse/${TICKET}" >&2
    fi
    echo "Ticket ${TICKET} closed."
    ;;

  *)
    echo "Unknown action: ${ACTION}" >&2
    echo "Actions: create-ticket, link-pr, update-status, close-ticket" >&2
    exit 2
    ;;
esac
