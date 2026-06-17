#!/usr/bin/env bash
# notify.sh — Send webhook notifications for release events.
# Usage: notify.sh <event> <message> [--webhook <url>]
# Events: phase_complete, phase_failed, build_ready, e2e_result, release_complete
set -euo pipefail

EVENT="${1:?Usage: notify.sh <event> <message>}"
MESSAGE="${2:?Usage: notify.sh <event> <message>}"
shift 2

WEBHOOK="${NOTIFICATION_WEBHOOK:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --webhook) WEBHOOK="$2"; shift 2 ;;
    *) shift ;;
  esac
done

if [[ -z "$WEBHOOK" ]]; then
  exit 0
fi

# Check if this event is in the configured events list
NOTIFICATION_EVENTS="${NOTIFICATION_EVENTS:-phase_complete,phase_failed,build_ready,e2e_result,release_complete}"
if ! echo "$NOTIFICATION_EVENTS" | grep -qw "$EVENT"; then
  exit 0
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Format based on detected webhook type
if echo "$WEBHOOK" | grep -q "hooks.slack.com"; then
  # Slack format
  PAYLOAD=$(jq -n \
    --arg text "*[OVMS Release] ${EVENT}*\n${MESSAGE}\n_${TIMESTAMP}_" \
    '{text: $text}')
elif echo "$WEBHOOK" | grep -q "chat.googleapis.com"; then
  # Google Chat format
  PAYLOAD=$(jq -n \
    --arg text "[OVMS Release] ${EVENT}\n${MESSAGE}\n${TIMESTAMP}" \
    '{text: $text}')
else
  # Generic JSON webhook
  PAYLOAD=$(jq -n \
    --arg event "$EVENT" \
    --arg message "$MESSAGE" \
    --arg timestamp "$TIMESTAMP" \
    --arg source "ovms-release" \
    '{event: $event, message: $message, timestamp: $timestamp, source: $source}')
fi

# Send notification (fire and forget — don't block release on notification failure)
HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" \
  -X POST \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  "$WEBHOOK" 2>/dev/null || echo "000")

if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "204" ]]; then
  echo "[NOTIFY] ${EVENT}: sent"
else
  echo "[NOTIFY] ${EVENT}: delivery failed (HTTP ${HTTP_CODE})" >&2
fi
