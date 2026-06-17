---
name: ovms-release
description: >-
  Interactive release orchestrator for OpenVINO Model Server (OVMS). Automates
  branch mirroring, CI config updates, patch application, tree transplant
  merges, and branch syncs across the ODH/RHOAI/RHDS pipeline. Maintains state
  across sessions for multi-day releases. Use when asked to do an OVMS release,
  sync OVMS branches, apply OVMS patches, or check OVMS release status.
allowed-tools: Bash Read Write Edit Glob Grep AskUserQuestion
user-invocable: true
argument-hint: "<version> | --resume | --status | --dry-run | --validate | --phase <name>"
compatibility: Requires git, gh CLI (authenticated to opendatahub-io and openshift orgs), python3, jq, patch, skopeo (optional — curl used as fallback for image queries), podman + oc (for E2E validation phases only — gracefully skipped if not installed)
metadata:
  author: AIPCC
  version: "1.0"
---

# OVMS Release Orchestrator

Interactive, feedback-driven release orchestrator for OpenVINO Model Server (OVMS).
Maintains state across sessions, runs deterministic phases autonomously, and pauses
for human judgment at critical points.

## Quick Reference

```
/ovms-release 2026.2              # Full release from Phase 0
/ovms-release --resume            # Continue from last checkpoint
/ovms-release --status            # Show current state (read-only)
/ovms-release --preflight         # Pre-flight only (no execution)
/ovms-release --dry-run 2026.2    # Simulate all phases
/ovms-release --phase sync-stable # Run specific phase
/ovms-release list                # Show all releases
/ovms-release notes               # Generate release notes
/ovms-release audit               # Generate compliance report
/ovms-release abort               # Abort current release
```

## State File

Location: `~/.ovms-release/openvino_model_server/<version>/release-state.yaml`

On `--resume`: loads state, renders narrative, continues from next pending phase.

## Prerequisites

Run `bash "${CLAUDE_SKILL_DIR}/scripts/check-prerequisites.sh"` to verify:
- `gh` CLI authenticated to opendatahub-io, openshift, red-hat-data-services orgs
- `git`, `python3`, `jq`, `patch`, `skopeo` installed
- `podman` or `docker` + `oc` for E2E phases (graceful skip if not installed)
- Git remotes configured: origin (fork), midstream (ODH), downstream (RHDS)

## Implementation

### Phase 0: Pre-flight Readiness Assessment (AUTONOMOUS)

**Always runs first.** Gathers all intelligence, produces Release Brief, asks user to confirm.

1. Run prerequisite check:
   ```bash
   bash "${CLAUDE_SKILL_DIR}/scripts/check-prerequisites.sh"
   ```

2. Run full pre-flight intelligence gathering:
   ```bash
   bash "${CLAUDE_SKILL_DIR}/scripts/preflight.sh" "${VERSION}"
   ```

3. Present the **Release Brief** to the user:
   - Upstream release status (detected version, commit count delta)
   - Dockerfile ARG changes (NEW/CHANGED/REMOVED with before→after values)
   - Python dependency versions (available vs pinned, compatibility matrix)
   - Patch health (`git apply --check` results: OK/FAILED per patch)
   - Fork sync warning (if fork is behind midstream)
   - Prerequisites status (all green / blockers identified)

4. Ask: "Ready to proceed with Phase 1? (yes / no / adjust config)"
   - If "adjust config": enter conversational mode to set base_image, driver_version, etc.

5. Save initial `release-state.yaml` with config populated.

6. **Jira integration (if configured):** Offer to create tracking ticket:
   ```
   Auto-create RHOAIENG Jira ticket for release ${VERSION}? (y/n)
   ```
   Uses tiered auth: acli → JIRA_API_TOKEN → MCP (graceful skip if unavailable).

**On resume:** Show abbreviated brief (what changed since last session) + narrative field.

---

### Phase 1: Mirror Branches (AUTONOMOUS)

Mirrors upstream release branches to opendatahub-io org.

1. Validate upstream branch exists in all 4 repos:
   ```bash
   bash "${CLAUDE_SKILL_DIR}/scripts/mirror-branches.sh" "${VERSION}" --validate
   ```

2. Create mirror branches with **repo-specific naming**:
   - `openvino_model_server` → `<YEAR>.<MINOR>-release` (e.g., `2026.2-release`)
   - `openvino`, `openvino.genai`, `openvino_tokenizers` → `releases/<YEAR>/<MINOR>`

3. Execute:
   ```bash
   bash "${CLAUDE_SKILL_DIR}/scripts/mirror-branches.sh" "${VERSION}"
   ```

4. **Tag the mirror point** for drift detection:
   ```bash
   git tag "odh-mirror-${VERSION}-$(date +%Y%m%d)" "${UPSTREAM_SHA}"
   ```

5. Verify branch creation via API, update state.
6. Send notification if configured.
7. Report result, ask: "Branches mirrored. Proceed to Phase 2 (OWNERS)?"

---

### Phase 2: Push OWNERS File (AUTONOMOUS)

Creates PR to add OWNERS file to the release branch on `openvino_model_server` only.

1. Execute:
   ```bash
   bash "${CLAUDE_SKILL_DIR}/scripts/push-owners.sh" "${VERSION}"
   ```

2. Creates PR from user's fork to `opendatahub-io/openvino_model_server` on the release branch.
3. Update state with PR URL.
4. Report: "OWNERS PR created at <URL>. Proceed to Phase 3?"

---

### Phase 3: ARG Diff Review (CONVERSATIONAL)

Compares Dockerfile.redhat ARGs between previous and current release.

1. Execute diff:
   ```bash
   bash "${CLAUDE_SKILL_DIR}/scripts/diff-args.sh" "${VERSION}"
   ```

2. Present structured diff to user:
   - NEW args (not in previous release)
   - CHANGED args (value differs)
   - REMOVED args (no longer present)

3. For each new/changed ARG, explain what it does and whether it needs attention.
4. Ask user to confirm the ARG set is correct.
5. Update state with confirmed build config values.

---

### Phase 3.5: Local Build Validation (HUMAN-ASSISTED)

Mandatory local build to catch issues early before CI.

1. Guide user through local build using `Dockerfile.redhat`
2. Verify build succeeds with the confirmed ARG values
3. Record pass/fail in state
4. On fail: enter conversational triage mode

---

### Phase 4: CI Config Update (AUTONOMOUS + HUMAN APPROVAL)

Generates openshift/release YAML and creates PR.

1. Generate CI config:
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/generate-ci-config.py" "${VERSION}"
   ```

2. **Validate generated YAML** (syntax + branch reference check).

3. Clone openshift/release, create branch, commit generated files.

4. Create PR via `gh pr create`.

5. Update state with CI config PR URL.

6. **PAUSE:** "CI config PR created at <URL>. Wait for /lgtm before proceeding to Phase 5."

---

### Phase 5: Apply Patches (CONVERSATIONAL)

Fetches patches from patches branch, applies them, creates PR.

1. Execute:
   ```bash
   bash "${CLAUDE_SKILL_DIR}/scripts/apply-patches.sh" "${VERSION}"
   ```

2. If patches apply cleanly: create PR, update state.
3. If conflicts: enter conversational mode to resolve.
   - Show conflicting hunks
   - Suggest resolution based on patch intent
   - Offer to invoke `/ovms-release-patch` for regeneration

4. After all patches applied: create `Dockerfile.konflux` from `Dockerfile.redhat`.
5. Apply label patch (04) to `Dockerfile.konflux`.
6. Create PR to midstream release branch.
7. Update state with patches PR URL.
8. **PAUSE:** "Patches PR created at <URL>. Wait for merge + Konflux build before Phase 5.5."

---

### Phase 5.5: ODH Image Verification (AUTONOMOUS)

Verifies the Konflux-built image exists after patches PR merges.

1. Wait for patches PR to be merged (check via `gh pr view --json state`).
2. Check image exists:
   ```bash
   skopeo inspect "docker://quay.io/opendatahub/openvino_model_server:pr-${PR_NUMBER}"
   ```
3. **Deep inspection:** verify `com.redhat.component` label matches expected value.
4. Update state.
5. Ask: "Image verified. Run E2E validation? (yes / skip)"

---

### Phase 5.7: E2E Validation — Release Branch Image (OPTIONAL)

Runs opendatahub-tests against the PR-built image.

1. Pre-checks: AWS creds exported, cluster reachable (`oc whoami --show-server`).
2. Execute:
   ```bash
   bash "${CLAUDE_SKILL_DIR}/scripts/run-e2e-tests.sh" \
     --image "quay.io/opendatahub/openvino_model_server:pr-${PR_NUMBER}" \
     --state-file "${STATE_FILE}"
   ```
3. On success: record passed in state, proceed to Phase 6.
4. On failure: block Phase 6, show output, enter triage mode.
5. On skip: record skip reason in state, proceed.

---

### Phase 6: Sync to Stable (AUTONOMOUS + VERIFICATION)

Tree transplant merge from release branch to stable.

1. Execute tree transplant:
   ```bash
   bash "${CLAUDE_SKILL_DIR}/scripts/tree-transplant.sh" "${VERSION}"
   ```
   Exit codes: 0=success, 1=git-failure, 2=awaiting git-clean confirmation.

2. If exit 2: show untracked files, ask user to confirm cleanup, then:
   ```bash
   bash "${CLAUDE_SKILL_DIR}/scripts/tree-transplant.sh" "${VERSION}" --confirm-clean
   ```

3. Run verification checks:
   ```bash
   bash "${CLAUDE_SKILL_DIR}/scripts/verify-sync.sh" "${VERSION}"
   ```
   - Check A: File content matches release branch (excluding protected files)
   - Check B: .tekton/ and .github/workflows/ preserved from stable
   - Check C: WORKSPACE file not modified

4. Create PR to stable branch. Commit message includes VERSION.
5. Update state.
6. **PAUSE:** "Stable sync PR created at <URL>. Wait for merge + Konflux build."

---

### Phase 6.5: E2E Validation — Stable Branch Image (OPTIONAL)

Runs opendatahub-tests against the Konflux-built stable image.

1. Detect stable image tag from quay.io API.
2. Pre-checks: same as Phase 5.7.
3. Execute:
   ```bash
   bash "${CLAUDE_SKILL_DIR}/scripts/run-e2e-tests.sh" \
     --image "quay.io/opendatahub/openvino_model_server:${STABLE_TAG}" \
     --state-file "${STATE_FILE}"
   ```
4. On success/failure/skip: same behavior as Phase 5.7.

---

### Phase 7: Sync Stable to RHOAI (AUTONOMOUS)

Syncs stable branch content to rhoai branch, removing Konflux-specific files.

1. Execute:
   ```bash
   bash "${CLAUDE_SKILL_DIR}/scripts/sync-to-rhoai.sh" "${VERSION}"
   ```
   Commit message: "Sync stable to rhoai (OVMS ${VERSION})"

2. Removes `.tekton/` and `.github/workflows/` from the sync.
3. Creates PR to rhoai branch.
4. Update state with RHOAI PR URL.
5. **PAUSE:** "RHOAI sync PR created at <URL>. Wait for merge → auto-sync to RHDS."

---

### Phase 8: RHDS Auto-sync Verification (MONITORING)

Monitors downstream auto-sync and final image availability.

1. Check RHDS sync status:
   ```bash
   bash "${CLAUDE_SKILL_DIR}/scripts/check-rhds-sync.sh" "${VERSION}"
   ```

2. Verify final image on quay.io:
   ```bash
   skopeo inspect "docker://quay.io/rhoai/odh-openvino-model-server-rhel9:rhoai-${RHOAI_VERSION}"
   ```

3. Record final image digest in state.

4. **Jira integration:** Transition tracking ticket to Done, add final digest as comment.

5. **Notification:** Send release_complete event.

6. Report: "Release complete! Final image: <digest>"

7. Offer: "Generate release notes? (y/n)"

---

## Error Recovery

- **Network failures:** Retry with exponential backoff (3 attempts).
- **Auth failures:** Guide user to re-authenticate (`gh auth login`, `acli jira auth`).
- **Patch conflicts:** Enter conversational mode, suggest `/ovms-release-patch`.
- **Build failures:** Show logs, suggest common fixes, offer to abort.
- **State corruption:** Validate state schema on load, offer fresh start if invalid.

## Session Handoff

The `narrative:` field in state provides human-readable context for session continuity.
On `--resume`, the skill renders this narrative before continuing, enabling any team
member to pick up where another left off.
