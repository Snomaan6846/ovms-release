# Architecture

## Design Principles

1. **Hybrid automation**: Autonomous for mechanical steps, human-in-loop for decisions
2. **State-driven**: All progress persists — safe to resume after interruption
3. **PR-only workflow**: No direct pushes to shared repositories
4. **Pluggable integrations**: Jira, Slack, E2E all optional and degradable
5. **Security-first**: No credential storage, delegate auth to external tools

## Component Structure

```
ovms-release/
├── .claude/skills/           # 6 skill definitions (SKILL.md)
│   ├── ovms-release/         # Main orchestration skill
│   ├── ovms-release-diff/    # Release comparison
│   ├── ovms-release-rebuild/ # CVE rebuild trigger
│   ├── ovms-release-hotfix/  # Cherry-pick to older releases
│   ├── ovms-release-patch/   # Patch diagnosis/regeneration
│   └── ovms-release-e2e/     # E2E validation runner
├── src/ovms_release/         # Python CLI (Typer)
│   ├── cli.py                # Entry points for all commands
│   ├── state.py              # State file R/W with migration
│   └── config.py             # Branch naming, repo maps
├── scripts/                  # Shell scripts (each phase)
├── templates/                # Jinja2 templates
├── references/               # Documentation
└── tests/                    # pytest suite
```

## Data Flow

```
User invokes /ovms-release <version>
        │
        ▼
┌─────────────────┐
│  SKILL.md       │  ← Claude reads this, drives conversation
│  (orchestrator) │
└────────┬────────┘
         │ calls
         ▼
┌─────────────────┐
│  scripts/*.sh   │  ← Actual git/gh operations
│  scripts/*.py   │
└────────┬────────┘
         │ updates
         ▼
┌─────────────────┐
│  state.yaml     │  ← ~/.ovms-release/<repo>/<version>/
│  (persistent)   │
└─────────────────┘
```

## State Machine

Each phase transitions through:
```
pending → in_progress → completed
                     └→ failed → (retry) → completed
```

The overall release state is:
```
in_progress → completed
           └→ aborted (with reason + timestamp)
```

## Security Model

| Concern | Approach |
|---------|----------|
| Git auth | Delegated to `gh` CLI (OAuth token) |
| Jira auth | Tiered: `acli` > env vars > skip |
| Notifications | Webhook URL in env/state (no token stored) |
| Cluster auth | `~/.kube/config` bind-mounted read-only |
| AWS creds | Environment variables only |
| State secrets | None stored — state contains URLs and status only |

## Integration Points

### Jira (Optional)
- Phase 0: Create tracking ticket
- Per-phase: Link PRs to ticket
- Phase 8: Close ticket

### Notifications (Optional)
- Events: phase_complete, phase_failed, build_ready, e2e_result, release_complete
- Transport: HTTP POST to webhook URL

### E2E (Optional)
- Phase 5.7: Validate release branch image
- Phase 6.5: Validate stable branch image
- Standalone: `/ovms-release-e2e <image>`
