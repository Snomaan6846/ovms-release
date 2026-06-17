"""Phase 6: Tree transplant sync to stable branch + verification.

Ports: tree-transplant.sh, verify-sync.sh
Fixes: ISSUE A (correct rm+checkout logic), ISSUE B (verify HEAD not stable)
"""

from __future__ import annotations

import contextlib
import subprocess
from typing import TYPE_CHECKING

from ovms_release import tools
from ovms_release.context import TreeTransplantResult

if TYPE_CHECKING:
    from ovms_release.context import ReleaseContext

PROTECTED_DIRS = [".tekton/", ".github/workflows/"]


def tree_transplant(ctx: ReleaseContext, *, confirm_clean: bool = False) -> TreeTransplantResult:
    """Perform tree transplant from release branch to stable.

    9-step process:
    1. Create/switch to PR branch
    2. Record protected files
    3. git rm -r (excluding protected)
    4. git checkout release branch content
    5. git rm --ignore-unmatch protected dirs from release content
    6. Restore protected from stable
    7. git add -A
    8. Check for untracked files
    9. Commit and push

    On second call (confirm_clean=True): switch to existing branch, clean, then commit.
    """
    release_branch = f"{ctx.year}.{ctx.minor}-release"
    stable_branch = "stable"
    pr_branch = f"sync-stable-{ctx.version}"

    tools.run_git("fetch", ctx.midstream_remote, release_branch)
    tools.run_git("fetch", ctx.midstream_remote, stable_branch)

    if confirm_clean:
        tools.run_git("switch", pr_branch)
        tools.run_git("clean", "-fd")
    else:
        try:
            tools.run_git("switch", "-c", pr_branch, f"{ctx.midstream_remote}/{stable_branch}")
        except subprocess.CalledProcessError:
            tools.run_git("switch", pr_branch)

    exclude_args = []
    for d in PROTECTED_DIRS:
        exclude_args.extend([f":(exclude){d}"])

    tools.run_git("rm", "-r", "--ignore-unmatch", "--", ".", *exclude_args)

    tools.run_git("checkout", f"{ctx.midstream_remote}/{release_branch}", "--", ".")

    tools.run_git("rm", "-r", "--ignore-unmatch", *PROTECTED_DIRS)

    for d in PROTECTED_DIRS:
        with contextlib.suppress(subprocess.CalledProcessError):
            tools.run_git("checkout", f"{ctx.midstream_remote}/{stable_branch}", "--", d)

    tools.run_git("add", "-A")

    status_out = tools.run_git("status", "--porcelain", capture=True)
    untracked = [line[3:] for line in status_out.stdout.decode().splitlines() if line.startswith("??")]

    if untracked and not confirm_clean:
        return TreeTransplantResult(success=False, needs_confirm=True, untracked_files=untracked)

    tools.run_git(
        "commit",
        "-m",
        f"Sync stable from {release_branch} for OVMS {ctx.version}",
        check=False,
    )

    if ctx.dry_run:
        return TreeTransplantResult(success=True)

    tools.run_git("push", "-u", ctx.fork_remote, pr_branch)

    pr_out = tools.run_gh(
        "pr",
        "create",
        "--repo",
        "opendatahub-io/openvino_model_server",
        "--base",
        stable_branch,
        "--title",
        f"Sync stable from {release_branch}",
        "--body",
        f"Tree transplant: sync stable branch from release for OVMS {ctx.version}.",
        capture=True,
    )
    return TreeTransplantResult(success=True, pr_url=pr_out.stdout.decode().strip())


def verify_sync(ctx: ReleaseContext) -> list[str]:
    """Verify the sync by comparing HEAD (PR branch) vs release branch.

    Fix for ISSUE B: compares HEAD vs release, NOT stable vs release.
    Returns list of discrepancies (empty = clean).
    """
    release_branch = f"{ctx.year}.{ctx.minor}-release"
    issues: list[str] = []

    diff_out = tools.run_git(
        "diff",
        "--name-only",
        "HEAD",
        f"{ctx.midstream_remote}/{release_branch}",
        "--",
        f":!{PROTECTED_DIRS[0]}",
        f":!{PROTECTED_DIRS[1]}",
        capture=True,
    )
    diff_files = [f for f in diff_out.stdout.decode().splitlines() if f.strip()]
    if diff_files:
        issues.append(f"Content divergence ({len(diff_files)} files differ from release): {', '.join(diff_files[:5])}")

    ls_out = tools.run_git(
        "ls-tree",
        "-r",
        "--name-only",
        "HEAD",
        *PROTECTED_DIRS,
        capture=True,
    )
    protected_files = ls_out.stdout.decode().splitlines()
    if not protected_files:
        issues.append("Protected directories (.tekton/, .github/workflows/) are missing from PR branch")

    return issues
