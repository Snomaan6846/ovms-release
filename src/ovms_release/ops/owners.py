"""Phase 2: Add OWNERS file to openvino_model_server release branch via PR.

Ports: push-owners.sh
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ovms_release import tools

if TYPE_CHECKING:
    from ovms_release.context import ReleaseContext

OWNERS_CONTENT = """\
approvers:
  - opendatahub-io/odh-model-runtimes

reviewers:
  - opendatahub-io/odh-model-runtimes
"""


def push_owners(ctx: ReleaseContext) -> str | None:
    """Create PR to add OWNERS file. Returns PR URL or None if no-op/dry-run."""
    midstream_branch = f"{ctx.year}.{ctx.minor}-release"
    pr_branch = f"add-owners-{ctx.version}"

    tools.run_git("fetch", ctx.midstream_remote, midstream_branch)

    try:
        tools.run_git("switch", "-c", pr_branch, f"{ctx.midstream_remote}/{midstream_branch}")
    except subprocess.CalledProcessError:
        tools.run_git("switch", pr_branch)

    with open("OWNERS", "w") as f:
        f.write(OWNERS_CONTENT)

    tools.run_git("add", "OWNERS")

    try:
        tools.run_git("diff", "--cached", "--quiet")
        tools.run_git("switch", "-")
        tools.run_git("branch", "-D", pr_branch, check=False)
        return None
    except subprocess.CalledProcessError:
        pass

    tools.run_git("commit", "-m", f"Add OWNERS file for {ctx.version} release branch")

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
        midstream_branch,
        "--title",
        f"Add OWNERS to {midstream_branch}",
        "--body",
        f"Add OWNERS file for the {ctx.version} release branch.",
        capture=True,
    )
    return pr_out.stdout.decode().strip()
