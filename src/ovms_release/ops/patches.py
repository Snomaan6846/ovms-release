"""Phase 5: Apply release patches from the patches branch.

Ports: apply-patches.sh, patch-update.sh
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ovms_release import tools

if TYPE_CHECKING:
    from ovms_release.context import ReleaseContext


class PatchError(Exception):
    """Raised when patch application fails."""


def _list_patches(midstream_remote: str) -> list[str]:
    """Get sorted list of patch files from patches branch."""
    out = tools.run_git(
        "ls-tree",
        "--name-only",
        f"{midstream_remote}/patches",
        capture=True,
    )
    patches = sorted(line for line in out.stdout.decode().splitlines() if line.strip())
    return patches


def check_patches(ctx: ReleaseContext) -> dict[str, bool]:
    """Pre-validate patches with git apply --check. Returns patch->applies mapping."""
    tools.run_git("fetch", ctx.midstream_remote, "patches", "--depth=1")

    patches = _list_patches(ctx.midstream_remote)
    results: dict[str, bool] = {}

    for patch in patches:
        try:
            show = tools.run_git(
                "show",
                f"{ctx.midstream_remote}/patches:{patch}",
                capture=True,
            )
            tools.run_git("apply", "--check", "-", stdin_data=show.stdout)
            results[patch] = True
        except subprocess.CalledProcessError:
            results[patch] = False

    return results


def apply_patches(ctx: ReleaseContext) -> str | None:
    """Apply patches and create PR. Returns PR URL or None on dry-run/no-patches.

    Raises PatchError if patches fail pre-validation or application.
    """
    midstream_branch = f"{ctx.year}.{ctx.minor}-release"
    pr_branch = f"apply-patches-{ctx.version}"

    tools.run_git("fetch", ctx.midstream_remote, "patches", "--depth=1")
    tools.run_git("fetch", ctx.midstream_remote, midstream_branch)

    try:
        tools.run_git("switch", "-c", pr_branch, f"{ctx.midstream_remote}/{midstream_branch}")
    except subprocess.CalledProcessError as e:
        raise PatchError(f"Cannot create branch from {ctx.midstream_remote}/{midstream_branch}") from e

    patches = _list_patches(ctx.midstream_remote)
    if not patches:
        tools.run_git("switch", "-")
        tools.run_git("branch", "-D", pr_branch, check=False)
        raise PatchError("No patches found on patches branch")

    patches_to_precheck = [p for p in patches if not p.startswith("04-")]
    failed_check = 0
    for patch in patches_to_precheck:
        try:
            show = tools.run_git(
                "show",
                f"{ctx.midstream_remote}/patches:{patch}",
                capture=True,
            )
            tools.run_git("apply", "--check", "-", stdin_data=show.stdout)
        except subprocess.CalledProcessError:
            failed_check += 1

    if failed_check > 0:
        tools.run_git("switch", "-")
        tools.run_git("branch", "-D", pr_branch, check=False)
        raise PatchError(f"{failed_check} patch(es) will fail to apply")

    failed_apply = 0
    for patch in patches:
        if patch.startswith("04-"):
            continue
        try:
            show = tools.run_git(
                "show",
                f"{ctx.midstream_remote}/patches:{patch}",
                capture=True,
            )
            tools.run_git("apply", "-", stdin_data=show.stdout)
            tools.run_git("add", "-A")
        except subprocess.CalledProcessError:
            failed_apply += 1

    tools.run_git("add", "-A")

    label_patches = [p for p in patches if p.startswith("04-")]
    for patch in label_patches:
        try:
            show = tools.run_git(
                "show",
                f"{ctx.midstream_remote}/patches:{patch}",
                capture=True,
            )
            tools.run_git("apply", "-", stdin_data=show.stdout)
            tools.run_git("add", "-A")
        except subprocess.CalledProcessError:
            failed_apply += 1

    if failed_apply > 0:
        raise PatchError(f"{failed_apply} patch(es) failed to apply")

    patch_list = "\n".join(f"- {p}" for p in patches)
    tools.run_git(
        "commit",
        "-m",
        f"Apply release patches for OVMS {ctx.version}\n\nPatches applied:\n{patch_list}",
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
        midstream_branch,
        "--title",
        f"Apply release patches for {ctx.version}",
        "--body",
        f"Applied patches from the patches branch for OVMS {ctx.version} release.",
        capture=True,
    )
    return pr_out.stdout.decode().strip()


def diagnose_patches(ctx: ReleaseContext) -> dict[str, str]:
    """Diagnose patch failures. Returns patch->error mapping for failed patches."""
    tools.run_git("fetch", ctx.midstream_remote, "patches", "--depth=1")

    patches = _list_patches(ctx.midstream_remote)
    failures: dict[str, str] = {}

    for patch in patches:
        try:
            show = tools.run_git(
                "show",
                f"{ctx.midstream_remote}/patches:{patch}",
                capture=True,
            )
            tools.run_git("apply", "--check", "-", stdin_data=show.stdout, capture=True)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().splitlines()[0] if e.stderr else "unknown error"
            failures[patch] = error_msg

    return failures
