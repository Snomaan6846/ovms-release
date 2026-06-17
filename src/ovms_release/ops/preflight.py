"""Preflight checks and intelligence gathering for OVMS releases.

Ports: preflight.sh, check-prerequisites.sh, detect-upstream-releases.sh
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING

from ovms_release import tools

if TYPE_CHECKING:
    from ovms_release.context import ReleaseContext

REQUIRED_TOOLS = ["git", "gh", "python3", "jq", "patch"]
OPTIONAL_TOOLS = ["skopeo"]
UPSTREAM_REPOS = ["model_server", "openvino", "openvino.genai", "openvino_tokenizers"]
UBI_REGISTRY = "registry.access.redhat.com"
UBI_REPO = "ubi9/ubi-minimal"


class PreflightError(Exception):
    """Raised when prerequisite checks fail."""


def check_prerequisites(ctx: ReleaseContext) -> list[str]:
    """Verify required tools, auth, and remotes. Return list of errors."""
    errors: list[str] = []

    for tool in REQUIRED_TOOLS:
        if not tools.check_tool(tool):
            errors.append(f"{tool} — not found")

    for tool in OPTIONAL_TOOLS:
        tools.check_tool(tool)

    e2e_enabled = os.environ.get("E2E_ENABLED", "false") == "true"
    if e2e_enabled:
        has_container = tools.check_tool("podman") or tools.check_tool("docker")
        if not has_container:
            errors.append("podman or docker — required for E2E phases")
        if not tools.check_tool("oc"):
            errors.append("oc — required for E2E phases")

    try:
        tools.run_gh("auth", "status", capture=True)
    except subprocess.CalledProcessError:
        errors.append("gh not authenticated — run: gh auth login")

    for remote in [ctx.fork_remote, ctx.midstream_remote, ctx.downstream_remote]:
        try:
            tools.run_git("remote", "get-url", remote, capture=True)
        except subprocess.CalledProcessError:
            errors.append(f"remote '{remote}' not configured")

    return errors


def detect_upstream_releases() -> list[str]:
    """Find upstream releases not yet mirrored. Returns list of version strings."""
    upstream_out = tools.run_gh(
        "api",
        "repos/openvinotoolkit/model_server/branches",
        "--paginate",
        "--jq",
        ".[].name",
        capture=True,
    )
    upstream_branches = sorted(
        line for line in upstream_out.stdout.decode().splitlines() if line.startswith("releases/")
    )

    mirrored_out = tools.run_gh(
        "api",
        "repos/opendatahub-io/openvino_model_server/branches",
        "--paginate",
        "--jq",
        ".[].name",
        capture=True,
    )
    mirrored_versions = set()
    for line in mirrored_out.stdout.decode().splitlines():
        if line.endswith("-release"):
            parts = line.removesuffix("-release").split(".")
            if len(parts) == 2:
                mirrored_versions.add(f"releases/{parts[0]}/{parts[1]}")

    new_releases = []
    for branch in upstream_branches:
        if branch not in mirrored_versions:
            version = branch.removeprefix("releases/").replace("/", ".")
            new_releases.append(version)

    return new_releases


def check_upstream_branches(ctx: ReleaseContext) -> dict[str, bool]:
    """Check which upstream repos have the expected release branch."""
    branch = f"releases/{ctx.year}/{ctx.minor}"
    results: dict[str, bool] = {}
    for repo in UPSTREAM_REPOS:
        try:
            tools.run_gh(
                "api",
                f"repos/openvinotoolkit/{repo}/branches/{branch}",
                "--jq",
                ".name",
                capture=True,
            )
            results[repo] = True
        except subprocess.CalledProcessError:
            results[repo] = False
    return results


def check_midstream_branch(ctx: ReleaseContext) -> bool:
    """Check if midstream release branch already exists."""
    branch = f"{ctx.year}.{ctx.minor}-release"
    try:
        tools.run_gh(
            "api",
            f"repos/opendatahub-io/openvino_model_server/branches/{branch}",
            "--jq",
            ".name",
            capture=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def check_patch_health(ctx: ReleaseContext) -> dict[str, bool]:
    """Check which patches apply cleanly to current HEAD."""
    results: dict[str, bool] = {}
    try:
        tools.run_git("fetch", ctx.midstream_remote, "patches", "--depth=1")
    except subprocess.CalledProcessError:
        return results

    try:
        ls_out = tools.run_git(
            "ls-tree",
            "--name-only",
            f"{ctx.midstream_remote}/patches",
            capture=True,
        )
    except subprocess.CalledProcessError:
        return results

    for patch in ls_out.stdout.decode().splitlines():
        if not patch.strip():
            continue
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


def check_ubi_tags() -> list[str]:
    """Query latest UBI base image tags via skopeo or empty list."""
    if not tools.check_tool("skopeo"):
        return []
    try:
        out = tools.run_cmd(
            "skopeo",
            "list-tags",
            f"docker://{UBI_REGISTRY}/{UBI_REPO}",
            capture=True,
        )
        data = json.loads(out.stdout)
        tags = sorted(
            (t for t in data.get("Tags", []) if t[0:1].isdigit() and "-" in t),
            reverse=True,
        )
        return tags[:5]
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return []


def check_fork_health(ctx: ReleaseContext) -> int | None:
    """Return how many commits fork is behind midstream, or None if unknown."""
    try:
        out = tools.run_git(
            "rev-list",
            f"{ctx.fork_remote}/main..{ctx.midstream_remote}/main",
            "--count",
            capture=True,
        )
        return int(out.stdout.decode().strip())
    except (subprocess.CalledProcessError, ValueError):
        return None


def run_preflight(ctx: ReleaseContext) -> None:
    """Full preflight: prereqs + release brief. Raises PreflightError on failure."""
    errors = check_prerequisites(ctx)
    if errors:
        raise PreflightError(f"{len(errors)} prerequisite(s) missing: {errors}")
