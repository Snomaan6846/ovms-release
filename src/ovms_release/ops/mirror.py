"""Phase 1: Mirror upstream release branches to ODH repos.

Ports: mirror-branches.sh
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ovms_release import tools

if TYPE_CHECKING:
    from ovms_release.context import ReleaseContext

REPO_MAP: dict[str, str] = {
    "model_server": "openvino_model_server",
    "openvino": "openvino",
    "openvino.genai": "openvino.genai",
    "openvino_tokenizers": "openvino_tokenizers",
}


class MirrorError(Exception):
    """Raised when mirroring fails for one or more repos."""


def _get_midstream_branch(midstream_repo: str, year: str, minor: str) -> str:
    if midstream_repo == "openvino_model_server":
        return f"{year}.{minor}-release"
    return f"releases/{year}/{minor}"


def _get_upstream_sha(upstream_repo: str, upstream_branch: str) -> str | None:
    """Query GitHub API for upstream branch SHA. Returns None if not found."""
    try:
        out = tools.run_gh(
            "api",
            f"repos/openvinotoolkit/{upstream_repo}/git/ref/heads/{upstream_branch}",
            "--jq",
            ".object.sha",
            capture=True,
        )
        sha = out.stdout.decode().strip()
        return sha if sha else None
    except subprocess.CalledProcessError:
        return None


def _branch_exists(midstream_repo: str, branch: str) -> str | None:
    """Check if midstream branch exists. Returns SHA if so, None otherwise."""
    try:
        out = tools.run_gh(
            "api",
            f"repos/opendatahub-io/{midstream_repo}/git/ref/heads/{branch}",
            "--jq",
            ".object.sha",
            capture=True,
        )
        sha = out.stdout.decode().strip()
        return sha if sha else None
    except subprocess.CalledProcessError:
        return None


def _create_branch(midstream_repo: str, branch: str, sha: str) -> bool:
    """Create a branch on the midstream repo. Returns True on success."""
    try:
        tools.run_gh(
            "api",
            f"repos/opendatahub-io/{midstream_repo}/git/refs",
            "-f",
            f"ref=refs/heads/{branch}",
            "-f",
            f"sha={sha}",
            capture=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def _create_tag(midstream_repo: str, tag: str, sha: str) -> bool:
    """Create a tag on the midstream repo. Returns True on success."""
    try:
        tools.run_gh(
            "api",
            f"repos/opendatahub-io/{midstream_repo}/git/refs",
            "-f",
            f"ref=refs/tags/{tag}",
            "-f",
            f"sha={sha}",
            capture=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def mirror_branches(ctx: ReleaseContext, *, validate_only: bool = False) -> dict[str, str]:
    """Mirror upstream branches to midstream. Returns repo->status mapping.

    Raises MirrorError if any repo fails.
    """
    upstream_branch = f"releases/{ctx.year}/{ctx.minor}"
    results: dict[str, str] = {}
    errors = 0

    for upstream_repo, midstream_repo in REPO_MAP.items():
        midstream_branch = _get_midstream_branch(midstream_repo, ctx.year, ctx.minor)

        upstream_sha = _get_upstream_sha(upstream_repo, upstream_branch)
        if not upstream_sha:
            results[upstream_repo] = "upstream_missing"
            errors += 1
            continue

        if validate_only:
            results[upstream_repo] = "validated"
            continue

        existing = _branch_exists(midstream_repo, midstream_branch)
        if existing:
            results[upstream_repo] = "already_exists"
            continue

        if ctx.dry_run:
            results[upstream_repo] = "dry_run"
            continue

        if not _create_branch(midstream_repo, midstream_branch, upstream_sha):
            results[upstream_repo] = "create_failed"
            errors += 1
            continue

        tag = f"odh-mirror-{ctx.version}-{datetime.now(tz=timezone.utc).strftime('%Y%m%d')}"
        _create_tag(midstream_repo, tag, upstream_sha)

        results[upstream_repo] = "created"

    if errors > 0:
        raise MirrorError(f"{errors} repo(s) failed during mirroring")

    return results
