# OVMS Release Skill — Project Conventions

## State File Location

State files live at `~/.ovms-release/openvino_model_server/<version>/release-state.yaml`
(NOT in the repo root — avoids dirtying the git working tree).

## CLI Commands

### Core release commands (`ovms-release`)
```bash
ovms-release preflight [VERSION]       # Phase 0: gather intelligence, produce Release Brief
ovms-release mirror <VERSION>          # Phase 1: create mirror branches in 4 repos
ovms-release owners <VERSION>          # Phase 2: push OWNERS file
ovms-release diff-args <VERSION>       # Phase 3: ARG diff report
ovms-release ci-config <VERSION>       # Phase 4: generate openshift/release PR
ovms-release patch <VERSION>           # Phase 5: apply patches, create PR
ovms-release sync-stable <VERSION>     # Phase 6: tree transplant to stable
ovms-release sync-rhoai                # Phase 7: sync stable to rhoai
ovms-release status                    # Show current release state
ovms-release resume                    # Continue from last checkpoint
ovms-release list                      # Show all releases with status/staleness
ovms-release notes [--version V]       # Generate release notes from state
ovms-release audit [--version V]       # Generate compliance audit report
ovms-release abort [--reason "..."]    # Abort current release with cleanup
```

### Standalone utility commands (separate CLI entry points)
```bash
ovms-release-diff <V1> <V2>                   # Read-only diff between two releases
ovms-release-rebuild [--branch <branch>]      # Trigger CVE rebuild via PR to downstream
ovms-release-hotfix <SHA> <BRANCH>            # Cherry-pick a fix to an older release
ovms-release-patch <VERSION>                  # Diagnose + regenerate failing patches
ovms-release-e2e <IMAGE-URL> [--from-state]   # Run E2E validation against any OVMS image
```

## Script Conventions

- All scripts use `set -euo pipefail`
- Tab-separated structured output (parseable by skill logic)
- Exit codes: 0=success, 1=user-fixable error, 2=argument/setup error, 3=duplicate/conflict
- Scripts invoked via `bash "${CLAUDE_SKILL_DIR}/scripts/<name>.sh" --args`
- `DRY_RUN=1` env var skips all destructive API calls (gh, git push)

## Security Model

- **No credential storage** in state files, config, or scripts
- **Auth delegation:** GitHub ops via `gh` CLI; Jira via `acli` or env vars
- **PR-only workflow:** NEVER push directly to midstream/downstream — ALL changes go through PRs
- **Protected files:** `.tekton/`, `.github/workflows/` excluded from syncs
- **Build arg safety:** `build-args.conf` must not contain secrets

## Branch Naming (CRITICAL)

| Repo | Upstream Branch | Midstream Branch |
|------|----------------|-----------------|
| openvino_model_server | `releases/YEAR/MINOR` | `YEAR.MINOR-release` (DIFFERENT!) |
| openvino | `releases/YEAR/MINOR` | `releases/YEAR/MINOR` (same) |
| openvino.genai | `releases/YEAR/MINOR` | `releases/YEAR/MINOR` (same) |
| openvino_tokenizers | `releases/YEAR/MINOR` | `releases/YEAR/MINOR` (same) |

Also note: upstream repo name is `model_server` (no `openvino_` prefix).

## Artifact Conventions

- Release notes: `~/.ovms-release/openvino_model_server/<version>/release-notes.md`
- Audit reports: `~/.ovms-release/openvino_model_server/<version>/audit-report.md`
- State backups: `~/.ovms-release/openvino_model_server/<version>/release-state.yaml.bak`
