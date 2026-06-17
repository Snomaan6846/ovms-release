---
name: ovms-release-patch
description: >-
  Diagnose and regenerate OVMS patch files when upstream structural changes
  break git apply. Run when patches show FAILED in pre-flight or when
  asked to fix/update OVMS patches.
allowed-tools: Bash Read Write Edit AskUserQuestion
user-invocable: true
argument-hint: "<version>"
---

# OVMS Patch Update

Diagnose patch failures, regenerate affected patches, validate the full set,
and push updates to the patches branch.

## Usage

```
/ovms-release-patch 2026.2
```

## Implementation

### Step 1: Diagnose Patch Failures

Fetch the patches branch and test each patch against the target release branch:

```bash
git fetch midstream patches --depth=1
git fetch midstream "${VERSION}-release" --depth=1

for patch in $(git ls-tree --name-only midstream/patches); do
  git show "midstream/patches:${patch}" | \
    git apply --check --directory=. - 2>&1
  # Record: patch_name → OK or FAILED (with error details)
done
```

Present diagnosis:
```
Patch Health Report for ${VERSION}:
  01-konflux-build-args.patch  OK
  02-dockerfile-python.patch   FAILED (hunk #2 at line 45 — context mismatch)
  03-rhoai-konflux.patch       FAILED (structural change at line 120)
  04-label.patch               OK
```

### Step 2: Regenerate Failing Patches

For each FAILED patch, offer two modes:

**Mode A: Claude-assisted mechanical regeneration**
1. Show the original patch intent (what it's trying to change)
2. Show the new file structure where it should apply
3. Generate the updated patch using `git diff`:
   ```bash
   # Make the intended change on a temp branch
   git switch -c patch-regen-${VERSION} midstream/${VERSION}-release
   # Apply the logical change (same intent, new context)
   # ... (conversational — ask user to confirm the change)
   git diff HEAD -- <target-file> > /tmp/regenerated-${patch_name}
   ```

**Mode B: User-guided manual edit**
1. Open the failing patch for manual editing
2. User makes corrections
3. Save to `/tmp/regenerated-${patch_name}`

### Step 3: Validate All Patches Together

Apply all patches sequentially on a temp branch to confirm no inter-patch conflicts:

```bash
git switch -c patch-validation-${VERSION} midstream/${VERSION}-release

# Overlay regenerated patches over originals
for f in /tmp/regenerated-*.patch; do
  [ -f "$f" ] || continue
  fname="$(basename "$f")"
  target="${fname#regenerated-}"
  cp "$f" "$target"
done

# Apply patches 01-03 in sequence
for patch in 01-*.patch 02-*.patch 03-*.patch; do
  git apply "${patch}" || { echo "CONFLICT in ${patch}"; exit 1; }
done

# Create Dockerfile.konflux (required before patch 04)
cp Dockerfile.redhat Dockerfile.konflux

# Apply patch 04 to Dockerfile.konflux
git apply 04-label.patch || { echo "CONFLICT in 04-label.patch"; exit 1; }

echo "All patches apply cleanly."

# Cleanup
rm -f Dockerfile.konflux 01-*.patch 02-*.patch 03-*.patch 04-*.patch
git switch -
git branch -D patch-validation-${VERSION}
```

### Step 4: Push Updated Patches

Create PR to update the patches branch:

```bash
git switch -c update-patches-${VERSION} midstream/patches

# Replace failing patches with regenerated versions
for f in /tmp/regenerated-*.patch; do
  [ -f "$f" ] || continue
  fname="$(basename "$f")"
  target="${fname#regenerated-}"
  cp "$f" "$target"
  git add "$target"
done

git commit -m "Update patches for ${VERSION} release (structural changes)"
git push -u origin update-patches-${VERSION}

gh pr create --repo opendatahub-io/openvino_model_server \
  --base patches \
  --title "Update patches for ${VERSION}" \
  --body "Regenerated patches to accommodate upstream structural changes."
```

### Step 5: Update Release State

If a release is in progress, set `apply_patches.patches_updated: true` in state.

## Error Handling

- **All patches OK:** Report "No patches need updating" and exit
- **Validation fails after regen:** Show which patch still fails, re-enter Step 2
- **Patches branch doesn't exist:** Error — patches branch is required
- **Network issues:** Retry fetch once, then report error
