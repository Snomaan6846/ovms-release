---
name: ovms-release-diff
description: >-
  Read-only diff between two OVMS releases. Shows Dockerfile ARG changes,
  commit count delta, and Python dep version differences. Use when asked to
  compare two OVMS releases or understand what changed between versions.
allowed-tools: Bash Read AskUserQuestion
user-invocable: true
argument-hint: "<v1> <v2>"
---

# OVMS Release Diff

Compare two OVMS releases to understand what changed between them.
This is a **read-only** operation — no branches are created or modified.

## Usage

```
/ovms-release-diff 2026.1 2026.2
```

## Implementation

### Step 1: Validate Arguments

Parse two version arguments (e.g., `2026.1` and `2026.2`).
Verify both release branches exist in `opendatahub-io/openvino_model_server`:
- V1 branch: `<YEAR1>.<MINOR1>-release`
- V2 branch: `<YEAR2>.<MINOR2>-release`

```bash
gh api "repos/opendatahub-io/openvino_model_server/branches/${V1_BRANCH}" --jq .name
gh api "repos/opendatahub-io/openvino_model_server/branches/${V2_BRANCH}" --jq .name
```

### Step 2: Dockerfile ARG Diff

Fetch `Dockerfile.redhat` from both branches and compare ARGs:

```bash
bash "${CLAUDE_SKILL_DIR}/scripts/diff-args.sh" "${V1}" "${V2}"
```

Present structured output:
- NEW: ARGs added in V2
- CHANGED: ARGs with different values
- REMOVED: ARGs present in V1 but not V2

### Step 3: Commit Count Delta

```bash
git log --oneline "midstream/${V1_BRANCH}..midstream/${V2_BRANCH}" | wc -l
```

### Step 4: Python Dependency Diff

Compare pinned versions of key packages between releases:
- openvino
- optimum-intel
- transformers
- jinja2

### Step 5: Present Report

Format as a clear comparison table and present to the user.

## Error Handling

- **Branch not found:** Report which version has no midstream branch
- **Network failure:** Retry once, then report error
- **No differences:** Report "versions are identical"
