---
name: ovms-release-e2e
description: >-
  Run opendatahub-tests E2E validation against any OVMS image on a RHOAI
  cluster. Accepts an image URL directly or auto-detects from release state.
  Use when asked to test an OVMS image or validate a release build.
allowed-tools: Bash Read AskUserQuestion
user-invocable: true
argument-hint: "<image-url> | --from-state [--smoke-only] [--test-filter <k>]"
---

# OVMS E2E Validation

Run the opendatahub-tests E2E suite against any OVMS image on a RHOAI cluster.
Can be invoked standalone or as part of the release flow (Phases 5.7/6.5).

## Usage

```
/ovms-release-e2e quay.io/opendatahub/openvino_model_server:pr-123
/ovms-release-e2e --from-state
/ovms-release-e2e quay.io/syedali/openvino_model_server:2026.2 --smoke-only
/ovms-release-e2e quay.io/syedali/openvino_model_server:2026.2 --test-filter="llm"
```

## Implementation

### Step 1: Determine Image URL

- If image URL provided directly: use it.
- If `--from-state`: load `release-state.yaml`, extract the appropriate image URL
  (release branch `pr-XXX` tag or stable branch tag depending on current phase).
- If neither: ask user for the image URL.

### Step 2: Pre-checks

Verify all prerequisites are met:

```bash
# Container runtime
command -v podman >/dev/null || command -v docker >/dev/null || \
  { echo "ERROR: podman or docker required"; exit 1; }

# OpenShift CLI
command -v oc >/dev/null || { echo "ERROR: oc CLI required"; exit 1; }

# Cluster connectivity
oc whoami --show-server || { echo "ERROR: Not logged into RHOAI cluster"; exit 1; }

# AWS credentials
[ -n "${AWS_ACCESS_KEY_ID:-}" ] || { echo "ERROR: AWS_ACCESS_KEY_ID not set"; exit 1; }
[ -n "${AWS_SECRET_ACCESS_KEY:-}" ] || { echo "ERROR: AWS_SECRET_ACCESS_KEY not set"; exit 1; }
```

### Step 3: Execute Tests

Load S3 configuration from state (or use defaults):

```bash
ODT_IMAGE="${config_opendatahub_tests_image:-quay.io/opendatahub/opendatahub-tests:latest}"
KUBECONFIG_PATH="${KUBECONFIG:-${HOME}/.kube/config}"

E2E_S3_BUCKET="${config_e2e_s3_bucket:-ods-ci-s3}"
E2E_S3_REGION="${config_e2e_s3_region:-us-east-1}"
E2E_S3_ENDPOINT="${config_e2e_s3_endpoint:-https://s3.us-east-1.amazonaws.com/}"
E2E_CI_S3_ENDPOINT="${config_e2e_ci_s3_endpoint:-https://s3.us-east-2.amazonaws.com/}"

# Build pytest args
PYTEST_ARGS="-v -s tests/model_serving/model_runtime/openvino/"
if [ "${SMOKE_ONLY}" = "true" ]; then
  PYTEST_ARGS="${PYTEST_ARGS} -k basic"
fi
if [ -n "${TEST_FILTER:-}" ]; then
  PYTEST_ARGS="${PYTEST_ARGS} -k ${TEST_FILTER}"
fi

podman run --rm \
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
    --ovms-runtime-image="${OVMS_IMAGE}"
```

### Step 4: Report Results

Parse pytest output for pass/fail counts. Report:
```
E2E Results:
  Tests run: 42
  Passed: 42
  Failed: 0
  Image: <OVMS_IMAGE>
  Cluster: <oc whoami --show-server output>
```

### Step 5: Update State (if mid-release)

If invoked from within a release flow (`--from-state`), update the appropriate
state field (`e2e_validation_release` or `e2e_validation_stable`) with results.

## Flags

| Flag | Effect |
|------|--------|
| `--from-state` | Auto-detect image from release state file |
| `--smoke-only` | Run quick smoke tests only (`pytest -k "basic"`) |
| `--test-filter <k>` | Pass `-k` filter to pytest (e.g., `--test-filter="llm"`) |
| `--test-path <path>` | Override default test path within container |

## Local Fallback Mode

If the container image is unavailable, fall back to local execution:
```bash
# Requires local clone of opendatahub-tests at config.opendatahub_tests_path
cd "${config_opendatahub_tests_path}"
uv run pytest ${PYTEST_ARGS} \
  --models-s3-bucket-name="${E2E_S3_BUCKET}" \
  --ovms-runtime-image="${OVMS_IMAGE}"
```

## Error Handling

- **Container runtime missing:** Error with install instructions
- **Cluster unreachable:** Guide user to `oc login`
- **AWS creds missing:** Guide user to export variables
- **Test failures:** Show failing test names and output, enter triage mode
- **Image not found:** Verify image URL is correct and accessible
