"""Generate release notes and audit reports.

Ports: generate-release-notes.sh, generate-audit-report.sh
Exports: generate_notes(ctx) -> Path, generate_audit(ctx) -> Path
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ovms_release import tools

if TYPE_CHECKING:
    from pathlib import Path

    from ovms_release.context import ReleaseContext


def generate_notes(ctx: ReleaseContext) -> Path:
    """Generate release notes from git log. Returns path to generated file."""
    release_branch = f"{ctx.year}.{ctx.minor}-release"
    stable_branch = f"{ctx.year}.{ctx.minor}-stable"

    try:
        log_out = tools.run_git(
            "log",
            "--oneline",
            "--no-merges",
            f"{ctx.midstream_remote}/{stable_branch}..{ctx.midstream_remote}/{release_branch}",
            capture=True,
        )
        commits = log_out.stdout.decode().strip()
    except subprocess.CalledProcessError:
        commits = "(unable to generate commit log)"

    notes_dir = ctx.state_dir / ctx.version
    notes_dir.mkdir(parents=True, exist_ok=True)
    output = notes_dir / "release-notes.md"

    content = f"""# OVMS {ctx.version} Release Notes

## Changes

{commits}

## Branches
- Release: `{release_branch}`
- Stable: `{stable_branch}`
"""
    output.write_text(content)
    return output


def generate_audit(ctx: ReleaseContext) -> Path:
    """Generate audit report with PR/image info. Returns path to generated file."""
    notes_dir = ctx.state_dir / ctx.version
    notes_dir.mkdir(parents=True, exist_ok=True)
    output = notes_dir / "audit-report.md"

    try:
        prs_out = tools.run_gh(
            "pr",
            "list",
            "--repo",
            "opendatahub-io/openvino_model_server",
            "--state",
            "all",
            "--search",
            f"{ctx.version}",
            "--json",
            "number,title,state,url",
            capture=True,
        )
        pr_data = prs_out.stdout.decode().strip()
    except subprocess.CalledProcessError:
        pr_data = "[]"

    content = f"""# OVMS {ctx.version} Audit Report

## Pull Requests
```json
{pr_data}
```

## Version: {ctx.version}
## Year: {ctx.year}
## Minor: {ctx.minor}
"""
    output.write_text(content)
    return output
