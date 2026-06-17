---
name: ovms-release-rebuild
description: >-
  Trigger a CVE rebuild of OVMS via PR to downstream. Creates minimal PR
  (base image bump or empty commit) to trigger Konflux pipeline on merge.
  Use when asked to rebuild OVMS for CVE fixes or base image updates.
allowed-tools: Bash Read Write AskUserQuestion
user-invocable: true
argument-hint: "[--branch <rhoai-version>]"
---

# OVMS CVE Rebuild

Trigger a Konflux rebuild of OVMS without code changes. Used when base image
CVEs are fixed or RPM updates are needed.

## Usage

```
/ovms-release-rebuild
/ovms-release-rebuild --branch rhoai-3.5
```

## Implementation

### Step 1: Determine Target Branch

If `--branch` provided, use it. Otherwise:
1. List available rhoai branches on downstream:
   ```bash
   gh api repos/red-hat-data-services/openvino_model_server/branches \
     --jq '.[].name' | grep '^rhoai-'
   ```
2. Ask user which branch to rebuild.

### Step 2: Pre-flight Check

1. Verify Konflux pipeline exists for the target branch.
2. Check current base image tag vs latest available:
   ```bash
   skopeo inspect "docker://registry.access.redhat.com/ubi9-minimal" \
     | jq -r '.Labels["version"]'
   ```

### Step 3: Base Image Bump (if needed)

If a newer UBI minor is available:
1. Update `FROM` tag in `Dockerfile.konflux`
2. Regenerate `rpms.lock.yaml` if base changed

### Step 4: Create PR Branch

```bash
git switch -c cve-rebuild-$(date +%Y%m%d) downstream/rhoai-${RHOAI_VERSION}

# If changes exist, commit them
git add Dockerfile.konflux rpms.lock.yaml
git commit -m "chore: CVE rebuild — bump base image to ${NEW_TAG} (OVMS ${VERSION})"

# If no file changes needed, create empty commit to trigger pipeline
git commit --allow-empty -m "chore: trigger CVE rebuild (OVMS ${VERSION})"
```

### Step 5: Push and Create PR

```bash
git push -u origin cve-rebuild-$(date +%Y%m%d)
gh pr create --repo red-hat-data-services/openvino_model_server \
  --base "rhoai-${RHOAI_VERSION}" \
  --title "CVE rebuild: OVMS ${VERSION}" \
  --body "Trigger Konflux rebuild for CVE remediation."
```

### Step 6: Monitor Pipeline

After PR is merged:
1. Watch Konflux pipeline status
2. Verify rebuilt image appears on quay.io

### Step 7: Verify Image

```bash
skopeo inspect "docker://quay.io/rhoai/odh-openvino-model-server-rhel9:rhoai-${RHOAI_VERSION}"
```

### Step 8: Optional E2E Gate

```
Rebuilt image available. Run E2E validation to confirm? (y/n)
```
On yes: invoke `/ovms-release-e2e <rebuilt-image>`.

## Error Handling

- **No Konflux pipeline:** Warn user, suggest manual trigger
- **Base image unchanged:** Offer empty commit path
- **Pipeline failure:** Show logs, suggest retry or escalation
