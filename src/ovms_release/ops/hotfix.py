"""Cherry-pick hotfixes to older release branches.

Ports: cherry-pick.sh
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ovms_release import tools

if TYPE_CHECKING:
    from ovms_release.context import ReleaseContext


class HotfixError(Exception):
    """Raised when cherry-pick fails."""


def cherry_pick(ctx: ReleaseContext, sha: str, target_branch: str) -> str | None:
    """Cherry-pick a commit to target branch. Returns PR URL or None.

    Uses ctx.downstream_remote for rhoai-* branches, midstream otherwise.
    """
    if target_branch.startswith("rhoai-"):
        target_repo = "red-hat-data-services/openvino_model_server"
        remote = ctx.downstream_remote
    else:
        target_repo = "opendatahub-io/openvino_model_server"
        remote = ctx.midstream_remote

    try:
        tools.run_git("show", "--oneline", sha, capture=True)
    except subprocess.CalledProcessError as e:
        raise HotfixError(f"Commit {sha} not found locally") from e

    tools.run_git("fetch", remote, target_branch)

    try:
        tools.run_git(
            "merge-base",
            "--is-ancestor",
            sha,
            f"{remote}/{target_branch}",
            capture=True,
        )
        return None
    except subprocess.CalledProcessError:
        pass

    pr_branch = f"cp-{sha[:8]}-to-{target_branch}"
    tools.run_git("switch", "-c", pr_branch, f"{remote}/{target_branch}")

    try:
        tools.run_git("cherry-pick", "-x", sha)
    except subprocess.CalledProcessError as e:
        raise HotfixError(f"Conflict during cherry-pick of {sha}. Resolve manually.") from e

    if ctx.dry_run:
        tools.run_git("switch", "-")
        tools.run_git("branch", "-D", pr_branch, check=False)
        return None

    tools.run_git("push", "-u", ctx.fork_remote, pr_branch)

    pr_out = tools.run_gh(
        "pr",
        "create",
        "--repo",
        target_repo,
        "--base",
        target_branch,
        "--title",
        f"Cherry-pick {sha[:8]} to {target_branch}",
        "--body",
        f"Cherry-pick of {sha} for hotfix.",
        capture=True,
    )
    return pr_out.stdout.decode().strip()
