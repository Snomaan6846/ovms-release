# Protected Files

Files that must be preserved during tree transplant merges (Phase 6: stable sync).

## Always Protected

These files exist on the `stable` branch and must NOT be overwritten by content from the release branch:

```
.tekton/                  # Tekton pipeline definitions for Konflux
.github/workflows/        # GitHub Actions workflows
```

## Rationale

- `.tekton/` pipelines are configured per-branch for Konflux CI/CD. Each branch has branch-specific pipeline references and build targets.
- `.github/workflows/` may contain branch-specific automation (e.g., release watchers, linting).

## During Tree Transplant

The `tree-transplant.sh` script:
1. Records protected files from stable before merge
2. Performs merge with `--strategy-option=theirs`
3. Restores protected files from stable
4. Verifies restoration via `verify-sync.sh`

## Phase 7 (rhoai sync)

When syncing to the `rhoai-*` branch:
- `.tekton/` is **removed** (not applicable downstream)
- `.github/workflows/` is **removed** (not applicable downstream)

This is intentional — the RHOAI branch has its own CI configuration managed separately.
