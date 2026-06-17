"""Phase 3: Dockerfile ARG diff between release branches.

Ports: diff-args.sh
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ovms_release import tools

if TYPE_CHECKING:
    from ovms_release.context import ReleaseContext


@dataclass
class ArgDiff:
    """Result of comparing Dockerfile ARGs between two versions."""

    added: dict[str, str] = field(default_factory=dict)
    removed: dict[str, str] = field(default_factory=dict)
    changed: dict[str, tuple[str, str]] = field(default_factory=dict)


class ArgDiffError(Exception):
    """Raised when Dockerfile.redhat cannot be read from a branch."""


def _extract_args(midstream_remote: str, branch: str) -> dict[str, str]:
    """Extract ARG key=value pairs from Dockerfile.redhat on a branch."""
    try:
        out = tools.run_git(
            "show",
            f"{midstream_remote}/{branch}:Dockerfile.redhat",
            capture=True,
        )
    except subprocess.CalledProcessError:
        return {}

    args: dict[str, str] = {}
    for line in out.stdout.decode().splitlines():
        stripped = line.strip()
        if stripped.startswith("ARG "):
            definition = stripped[4:]
            if "=" in definition:
                key, value = definition.split("=", 1)
                args[key.strip()] = value.strip()
            else:
                args[definition.strip()] = ""
    return args


def diff_args(ctx: ReleaseContext, old_version: str | None = None) -> ArgDiff:
    """Compare Dockerfile ARGs between old and new release branches.

    If old_version is None, defaults to the previous minor version.
    Raises ArgDiffError if either branch's Dockerfile.redhat is unreadable.
    """
    if old_version is None:
        prev_minor = int(ctx.minor) - 1
        old_version = f"{ctx.year}.{prev_minor}"

    old_year, old_minor = old_version.split(".")
    old_branch = f"{old_year}.{old_minor}-release"
    new_branch = f"{ctx.year}.{ctx.minor}-release"

    old_args = _extract_args(ctx.midstream_remote, old_branch)
    if not old_args:
        raise ArgDiffError(f"Could not read Dockerfile.redhat from {ctx.midstream_remote}/{old_branch}")

    new_args = _extract_args(ctx.midstream_remote, new_branch)
    if not new_args:
        raise ArgDiffError(f"Could not read Dockerfile.redhat from {ctx.midstream_remote}/{new_branch}")

    old_keys = set(old_args.keys())
    new_keys = set(new_args.keys())

    result = ArgDiff()

    for key in sorted(new_keys - old_keys):
        result.added[key] = new_args[key]

    for key in sorted(old_keys - new_keys):
        result.removed[key] = old_args[key]

    for key in sorted(old_keys & new_keys):
        if old_args[key] != new_args[key]:
            result.changed[key] = (old_args[key], new_args[key])

    return result
