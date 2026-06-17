"""CVE rebuild: trigger Konflux rebuild via PR.

Ports: cve-rebuild.sh
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ovms_release import tools

if TYPE_CHECKING:
    from ovms_release.context import ReleaseContext


class RebuildError(Exception):
    """Raised when rebuild operation fails."""


def cve_rebuild(
    ctx: ReleaseContext,
    branch: str,
    *,
    bump_base: bool = False,
) -> str | None:
    """Trigger CVE rebuild. Returns PR URL or None on dry-run.

    Args:
        ctx: Release context.
        branch: Target branch to rebuild.
        bump_base: If True, append timestamp to Dockerfile. Otherwise empty commit.
    """
    date_str = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    pr_branch = f"cve-rebuild-{branch}-{date_str}"
    remote = ctx.downstream_remote if branch.startswith("rhoai-") else ctx.midstream_remote
    target_repo = (
        "red-hat-data-services/openvino_model_server"
        if branch.startswith("rhoai-")
        else "opendatahub-io/openvino_model_server"
    )

    tools.run_git("fetch", remote, branch)

    try:
        tools.run_git("switch", "-c", pr_branch, f"{remote}/{branch}")
    except subprocess.CalledProcessError as e:
        raise RebuildError(f"Cannot create branch from {remote}/{branch}") from e

    if bump_base:
        tools.run_cmd(
            "bash",
            "-c",
            f'echo "# CVE rebuild trigger: {date_str}" >> Dockerfile.redhat',
        )
        tools.run_git("add", "Dockerfile.redhat")
        tools.run_git("commit", "-m", f"CVE rebuild: bump base image timestamp ({date_str})")
    else:
        tools.run_git(
            "commit",
            "--allow-empty",
            "-m",
            f"CVE rebuild: trigger Konflux rebuild ({date_str})",
        )

    if ctx.dry_run:
        tools.run_git("switch", "-")
        tools.run_git("branch", "-D", pr_branch, check=False)
        return None

    tools.run_git("push", "-u", ctx.fork_remote, pr_branch)

    strategy = "base image bump" if bump_base else "empty commit"
    pr_out = tools.run_gh(
        "pr",
        "create",
        "--repo",
        target_repo,
        "--base",
        branch,
        "--title",
        f"CVE rebuild: {branch} ({date_str})",
        "--body",
        f"Trigger Konflux rebuild for CVE patching.\n\nStrategy: {strategy}\nDate: {date_str}",
        capture=True,
    )
    return pr_out.stdout.decode().strip()
