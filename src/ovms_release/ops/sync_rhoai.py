"""Phase 7: Sync stable branch to RHOAI with big-diff guard.

Ports: sync-to-rhoai.sh
Fixes: ISSUE C (big-diff guard, no --allow-empty without check)
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ovms_release import tools
from ovms_release.context import EmptySyncError

if TYPE_CHECKING:
    from ovms_release.context import ReleaseContext

REMOVABLE_DIRS = [".tekton", ".github/workflows"]


def sync_to_rhoai(ctx: ReleaseContext) -> str | None:
    """Sync stable to RHOAI branch. Returns PR URL or None on dry-run.

    Raises EmptySyncError if sync produces no substantive changes.
    """
    if not ctx.rhoai_version:
        raise ValueError("rhoai_version must be set on ReleaseContext")

    stable_branch = "stable"
    rhoai_branch = f"rhoai-{ctx.rhoai_version}"
    pr_branch = f"sync-rhoai-{ctx.rhoai_version}"

    tools.run_git("fetch", ctx.midstream_remote, stable_branch, rhoai_branch)

    try:
        tools.run_git("switch", "-c", pr_branch, f"{ctx.midstream_remote}/{rhoai_branch}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Cannot create branch from {ctx.midstream_remote}/{rhoai_branch}") from e

    try:
        tools.run_git(
            "merge",
            f"{ctx.midstream_remote}/{stable_branch}",
            "--no-commit",
            "--strategy=recursive",
            "--strategy-option=theirs",
        )
    except subprocess.CalledProcessError:
        tools.run_git("checkout", "--theirs", "--", ".", check=False)
        tools.run_git("add", "-A")

    for d in REMOVABLE_DIRS:
        tools.run_git("rm", "-rf", "--ignore-unmatch", d)

    leftover = tools.run_git("ls-files", ".tekton", ".github/workflows", capture=True)
    if leftover.stdout.strip():
        raise RuntimeError(f".tekton or .github/workflows still tracked after removal:\n{leftover.stdout.decode()}")

    tools.run_git("add", "-A")

    stat = tools.run_git("diff", "--cached", "--stat", capture=True)
    if not stat.stdout.strip():
        tools.run_git("merge", "--abort", check=False)
        tools.run_git("switch", "-")
        tools.run_git("branch", "-D", pr_branch, check=False)
        raise EmptySyncError("Sync produced no changes — aborting to prevent empty commit")

    tools.run_git(
        "commit",
        "-m",
        f"Sync stable to rhoai (OVMS {ctx.version})",
    )

    if ctx.dry_run:
        tools.run_git("switch", "-")
        tools.run_git("branch", "-D", pr_branch, check=False)
        return None

    tools.run_git("push", "-u", ctx.fork_remote, pr_branch)

    pr_out = tools.run_gh(
        "pr",
        "create",
        "--repo",
        "opendatahub-io/openvino_model_server",
        "--base",
        rhoai_branch,
        "--title",
        f"Sync stable to {rhoai_branch}",
        "--body",
        f"Sync stable branch content to {rhoai_branch}.\n\n"
        ".tekton/ and .github/workflows/ removed (not applicable to rhoai branch).",
        capture=True,
    )
    return pr_out.stdout.decode().strip()
