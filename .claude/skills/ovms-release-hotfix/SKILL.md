---
name: ovms-release-hotfix
description: >-
  Cherry-pick a commit to an older OVMS release branch. Tries GitHub webui
  first, falls back to command-line for conflict resolution. Use when asked
  to backport a fix to a previous OVMS release.
allowed-tools: Bash Read AskUserQuestion
user-invocable: true
argument-hint: "<commit-sha> <target-branch>"
---

# OVMS Hotfix Cherry-pick

Cherry-pick a specific commit to an older release branch. Useful for
backporting critical fixes to already-released versions.

## Usage

```
/ovms-release-hotfix abc1234 rhoai-3.4
/ovms-release-hotfix abc1234 2025.4-release
```

## Implementation

### Step 0: Suggest WebUI First

Before proceeding with command-line operations:
```
First try creating a PR via the GitHub webui (compare view). If it applies
cleanly with no merge conflicts, that's faster. Only proceed with this
command-line flow if the webui reports merge conflicts.

Continue with command-line cherry-pick? (yes / no)
```

### Step 1: Validate Arguments

1. Confirm commit exists locally:
   ```bash
   git show --oneline "${COMMIT_SHA}" || { echo "Commit not found locally"; exit 1; }
   ```

2. Fetch target branch:
   ```bash
   git fetch "${REMOTE}" "${TARGET_BRANCH}"
   ```

### Step 2: Check Ancestor

Verify fix isn't already on the target:
```bash
if git merge-base --is-ancestor "${COMMIT_SHA}" "${REMOTE}/${TARGET_BRANCH}"; then
  echo "Commit is already an ancestor of ${TARGET_BRANCH} — nothing to do."
  exit 0
fi
```

### Step 3: Create PR Branch

```bash
git switch -c "cp-${COMMIT_SHA:0:8}-to-${TARGET_BRANCH}" "${REMOTE}/${TARGET_BRANCH}"
```

### Step 4: Cherry-pick

```bash
git cherry-pick -x "${COMMIT_SHA}"
```

If conflict: enter conversational mode.
- Show conflicting files with `git diff --name-only --diff-filter=U`
- Display conflict markers for each file
- Help user resolve interactively
- After resolution: `git add . && git cherry-pick --continue`

### Step 5: Push and Create PR

Determine correct target repo based on branch name:
- Branch starts with `rhoai-` → PR to `red-hat-data-services/openvino_model_server`
- Version branch (e.g., `2025.4-release`) → PR to `opendatahub-io/openvino_model_server`

```bash
git push -u origin "cp-${COMMIT_SHA:0:8}-to-${TARGET_BRANCH}"
gh pr create --repo "${TARGET_REPO}" \
  --base "${TARGET_BRANCH}" \
  --title "Cherry-pick ${COMMIT_SHA:0:8} to ${TARGET_BRANCH}" \
  --body "Cherry-pick of ${COMMIT_SHA} for hotfix."
```

### Step 6: Report

```
PR created: <URL>
Target: ${TARGET_REPO} / ${TARGET_BRANCH}
```

## Error Handling

- **Commit not found:** Ask user to verify SHA and ensure local repo is up to date
- **Merge conflict:** Enter interactive resolution mode
- **Branch doesn't exist:** List available branches, ask user to pick correct one
- **Permission denied:** Verify user has fork access to target repo

## Notes

No state file is used — cherry-picks are one-shot operations, not multi-day workflows.
