"""Check RHDS (Red Hat Data Services) sync status.

Ports: check-rhds-sync.sh (GAP 1 — was missing from v1)
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ovms_release import tools

if TYPE_CHECKING:
    from ovms_release.context import ReleaseContext


def check_rhds_sync(ctx: ReleaseContext) -> dict[str, str]:
    """Check sync status between midstream and downstream branches.

    Returns a mapping of branch->status.
    """
    results: dict[str, str] = {}
    rhoai_branch = f"rhoai-{ctx.rhoai_version}" if ctx.rhoai_version else None
    stable_branch = f"{ctx.year}.{ctx.minor}-stable"

    if not rhoai_branch:
        return {"error": "rhoai_version not set"}

    try:
        tools.run_git("fetch", ctx.downstream_remote, rhoai_branch)
    except subprocess.CalledProcessError:
        results[rhoai_branch] = "fetch_failed"
        return results

    try:
        tools.run_git("fetch", ctx.midstream_remote, stable_branch)
    except subprocess.CalledProcessError:
        results[stable_branch] = "fetch_failed"
        return results

    try:
        count_out = tools.run_git(
            "rev-list",
            "--count",
            f"{ctx.downstream_remote}/{rhoai_branch}..{ctx.midstream_remote}/{stable_branch}",
            capture=True,
        )
        behind = int(count_out.stdout.decode().strip())
        if behind == 0:
            results[rhoai_branch] = "in_sync"
        else:
            results[rhoai_branch] = f"behind_by_{behind}"
    except (subprocess.CalledProcessError, ValueError):
        results[rhoai_branch] = "comparison_failed"

    return results
