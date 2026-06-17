# Phase Implementation Details

## Phase 4: CI Configuration

### Overview

Phase 4 generates the CI/CD configuration required by `openshift/release` to build OVMS images. This config tells Prow how to build, test, and promote images from the ODH midstream repository.

### Files Generated

The script `generate-ci-config.py` produces a YAML file following the `openshift/release` ci-operator schema:

```yaml
org: opendatahub-io
repo: openvino_model_server
branch: YEAR.MINOR-release
variants:
  v4.14:
    build_root_image: ...
    images: ...
    promotion: ...
    resources: ...
tests: ...
```

### Placement

The generated config is placed in:
```
openshift/release/ci-operator/config/opendatahub-io/openvino_model_server/
```

### Validation Steps

After generation, two automatic checks run:
1. **YAML syntax validation** — ensures the file is parseable
2. **Branch reference validation** — ensures internal references match the target version

### PR Workflow

1. Clone/update your fork of `openshift/release`
2. Generate config: `generate-ci-config.py 2026.2 --output <path>`
3. Create PR against `openshift/release:master`
4. Wait for Prow presubmit checks to pass
5. Merge (requires LGTM from approver)

### Dependency

Phase 4 depends on Phase 1 (mirror branches must exist) because the CI config references the midstream branch.

---

## Phase 5: Patch Application

### Patch Ordering

Patches are stored on the `patches` branch as numbered files:
```
01-base-image-swap.patch     # UBI base image replacement
02-build-flags.patch         # Compilation flag adjustments
03-python-deps.patch         # Python dependency pinning
04-konflux-labels.patch      # Dockerfile.konflux label addition
```

### Execution Order

1. Patches 01-03 applied to `Dockerfile.redhat`
2. `Dockerfile.konflux` created as copy of `Dockerfile.redhat`
3. Patch 04 applied to `Dockerfile.konflux` (adds Konflux-specific labels)

### Conflict Resolution

If a patch fails `git apply`:
- The script reports which hunk failed
- User must regenerate the patch (see `/ovms-release-patch`)
- Re-run `apply-patches.sh` after regeneration

---

## Phase 6: Tree Transplant

### Why Tree Transplant?

A regular merge would bring release branch's full Git history and potentially introduce conflicts with stable's protected files. Tree transplant takes only the **file content** from the release branch while preserving stable's merge history.

### Algorithm

```
1. git merge <release> --no-commit --strategy=recursive --strategy-option=theirs
2. Restore .tekton/ and .github/workflows/ from stable
3. Verify: content matches release (except protected files)
4. Single commit on stable
```

### Protected File Restoration

The script records all files under `.tekton/` and `.github/workflows/` BEFORE the merge, then uses `git checkout <stable> -- <file>` to restore each one after the theirs-strategy merge overwrites them.
