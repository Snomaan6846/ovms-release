# ovms-release

Interactive release orchestrator for OpenVINO Model Server (OVMS). Automates branch mirroring, CI config updates, patch application, tree transplant merges, and branch syncs across the ODH/RHOAI/RHDS pipeline.

## Quick Start

```bash
# Install as Cursor skill (symlink)
ln -sf ~/Workspace/repos/ovms-release ~/.cursor/skills/ovms-release

# Or install via pip
pip install -e .

# Or install as Claude Code plugin
/plugin install https://github.com/Snomaan6846/ovms-release
```

## Usage

### Main Release Flow

```
/ovms-release 2026.2       # Full release (pre-flight through Phase 8)
/ovms-release --resume     # Continue from last checkpoint
/ovms-release --status     # Show current release state
/ovms-release --preflight  # Pre-flight only (no execution)
```

### Utility Skills

```
/ovms-release-diff 2026.1 2026.2     # Compare two releases
/ovms-release-rebuild                 # Trigger CVE rebuild
/ovms-release-hotfix <sha> <branch>   # Cherry-pick to older release
/ovms-release-patch 2026.2            # Diagnose/fix failing patches
/ovms-release-e2e <image-url>         # Run E2E validation
```

### CLI Commands

```bash
ovms-release preflight 2026.2    # Phase 0
ovms-release mirror 2026.2       # Phase 1
ovms-release status              # Show state
ovms-release list                # All releases
ovms-release notes               # Generate release notes
ovms-release audit               # Compliance report
ovms-release abort --reason "x"  # Abort with cleanup
```

## Prerequisites

- `git`, `gh` (authenticated), `python3`, `jq`, `patch`
- Optional: `skopeo`, `podman`/`docker`, `oc` (for E2E)
- Optional: `acli` or `JIRA_API_TOKEN` (for Jira integration)

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for design details.

## Configuration

State files live at `~/.ovms-release/openvino_model_server/<version>/release-state.yaml`.

Jira integration is tiered:
1. `acli` CLI (preferred)
2. Environment variables (`JIRA_API_TOKEN`, `JIRA_USER_EMAIL`)
3. Graceful skip (state-file only tracking)

Notifications via webhook URL in state config or `NOTIFICATION_WEBHOOK` env var.

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## License

Apache-2.0
