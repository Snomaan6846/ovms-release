#!/usr/bin/env bash
# run-e2e-tests.sh — Run opendatahub-tests container for E2E validation.
# Auto-selects podman or docker, handles KUBECONFIG, creds, fallback to local mode.
# Usage: run-e2e-tests.sh --image <URL> [--from-state] [--smoke-only] [--test-filter <k>] [--test-path <p>] [--state-file <f>]
set -euo pipefail

IMAGE=""
FROM_STATE=false
SMOKE_ONLY=false
TEST_FILTER=""
TEST_PATH="tests/model_serving/model_runtime/openvino/"
STATE_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --image) IMAGE="$2"; shift 2 ;;
    --from-state) FROM_STATE=true; shift ;;
    --smoke-only) SMOKE_ONLY=true; shift ;;
    --test-filter) TEST_FILTER="$2"; shift 2 ;;
    --test-path) TEST_PATH="$2"; shift 2 ;;
    --state-file) STATE_FILE="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Determine container runtime
if command -v podman &>/dev/null; then
  RUNTIME="podman"
elif command -v docker &>/dev/null; then
  RUNTIME="docker"
else
  echo "ERROR: podman or docker required for E2E tests" >&2
  exit 1
fi

# Pre-checks
if ! command -v oc &>/dev/null; then
  echo "ERROR: oc CLI required" >&2
  exit 1
fi

if ! oc whoami --show-server &>/dev/null 2>&1; then
  echo "ERROR: Not logged into a cluster (run: oc login)" >&2
  exit 1
fi

if [[ -z "${AWS_ACCESS_KEY_ID:-}" ]]; then
  echo "ERROR: AWS_ACCESS_KEY_ID not set" >&2
  exit 1
fi

if [[ -z "${AWS_SECRET_ACCESS_KEY:-}" ]]; then
  echo "ERROR: AWS_SECRET_ACCESS_KEY not set" >&2
  exit 1
fi

# Resolve image
if [[ -z "$IMAGE" && "$FROM_STATE" == "true" ]]; then
  echo "ERROR: --from-state requires state file parsing (use CLI wrapper)" >&2
  exit 2
fi

if [[ -z "$IMAGE" ]]; then
  echo "ERROR: --image <URL> required" >&2
  exit 2
fi

# Config from environment (populated from state by caller)
ODT_IMAGE="${ODT_IMAGE:-quay.io/opendatahub/opendatahub-tests:latest}"
KUBECONFIG_PATH="${KUBECONFIG:-${HOME}/.kube/config}"
E2E_S3_BUCKET="${E2E_S3_BUCKET:-ods-ci-s3}"
E2E_S3_REGION="${E2E_S3_REGION:-us-east-1}"
E2E_S3_ENDPOINT="${E2E_S3_ENDPOINT:-https://s3.us-east-1.amazonaws.com/}"
E2E_CI_S3_ENDPOINT="${E2E_CI_S3_ENDPOINT:-https://s3.us-east-2.amazonaws.com/}"

# Build pytest args
PYTEST_ARGS="-v -s ${TEST_PATH}"
if [[ "$SMOKE_ONLY" == "true" ]]; then
  PYTEST_ARGS="${PYTEST_ARGS} -k basic"
fi
if [[ -n "$TEST_FILTER" ]]; then
  PYTEST_ARGS="${PYTEST_ARGS} -k ${TEST_FILTER}"
fi

echo "=== E2E Validation ==="
echo "Runtime: ${RUNTIME}"
echo "Image under test: ${IMAGE}"
echo "Test image: ${ODT_IMAGE}"
echo "Cluster: $(oc whoami --show-server 2>/dev/null)"
echo ""

# Execute
$RUNTIME run --rm \
  -e AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
  -e AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
  -e KUBECONFIG=/kube/config \
  -v "${KUBECONFIG_PATH}:/kube/config:ro" \
  "${ODT_IMAGE}" \
  pytest ${PYTEST_ARGS} \
    --models-s3-bucket-name="${E2E_S3_BUCKET}" \
    --models-s3-bucket-region="${E2E_S3_REGION}" \
    --models-s3-bucket-endpoint="${E2E_S3_ENDPOINT}" \
    --ci-s3-bucket-endpoint="${E2E_CI_S3_ENDPOINT}" \
    --ovms-runtime-image="${IMAGE}"

echo ""
echo "E2E tests completed successfully."
