"""Thin subprocess wrappers for external tool invocations.

All ops/ modules must import this module as:
    from ovms_release import tools
    tools.run_git(...)

Never use: from ovms_release.tools import run_git  (breaks mock patching)
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Literal, overload


@overload
def run_cmd(
    tool: str,
    *args: str,
    check: bool = ...,
    capture: Literal[True],
    stdin_data: bytes | None = ...,
) -> subprocess.CompletedProcess[bytes]: ...


@overload
def run_cmd(
    tool: str,
    *args: str,
    check: bool = ...,
    capture: Literal[False] = ...,
    stdin_data: bytes | None = ...,
) -> subprocess.CompletedProcess[None]: ...


def run_cmd(
    tool: str,
    *args: str,
    check: bool = True,
    capture: bool = False,
    stdin_data: bytes | None = None,
) -> subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[None]:
    """Generic subprocess wrapper -- single mock target for all external calls.

    Args:
        tool: The executable name (git, gh, skopeo, oc, make, etc.)
        *args: Command arguments.
        check: If True, raise CalledProcessError on non-zero exit.
        capture: If True, buffer stdout/stderr (for parsing).
                 If False (default), stream live to terminal.
        stdin_data: Bytes piped to subprocess stdin (for pipe chain patterns).

    Returns:
        CompletedProcess[bytes] when capture=True (.stdout is bytes).
        CompletedProcess[None] when capture=False (.stdout is None).
    """
    cmd = [tool, *args]
    if capture:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=True,
            input=stdin_data,
        )
        return result
    else:
        result = subprocess.run(
            cmd,
            check=check,
            input=stdin_data,
        )
        return result


@overload
def run_git(
    *args: str,
    check: bool = ...,
    capture: Literal[True],
    stdin_data: bytes | None = ...,
) -> subprocess.CompletedProcess[bytes]: ...


@overload
def run_git(
    *args: str,
    check: bool = ...,
    capture: Literal[False] = ...,
    stdin_data: bytes | None = ...,
) -> subprocess.CompletedProcess[None]: ...


def run_git(
    *args: str,
    check: bool = True,
    capture: bool = False,
    stdin_data: bytes | None = None,
) -> subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[None]:
    """Run a git command."""
    return run_cmd("git", *args, check=check, capture=capture, stdin_data=stdin_data)  # type: ignore[call-overload, no-any-return]


@overload
def run_gh(
    *args: str,
    check: bool = ...,
    capture: Literal[True],
    stdin_data: bytes | None = ...,
) -> subprocess.CompletedProcess[bytes]: ...


@overload
def run_gh(
    *args: str,
    check: bool = ...,
    capture: Literal[False] = ...,
    stdin_data: bytes | None = ...,
) -> subprocess.CompletedProcess[None]: ...


def run_gh(
    *args: str,
    check: bool = True,
    capture: bool = False,
    stdin_data: bytes | None = None,
) -> subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[None]:
    """Run a gh (GitHub CLI) command."""
    return run_cmd("gh", *args, check=check, capture=capture, stdin_data=stdin_data)  # type: ignore[call-overload, no-any-return]


@overload
def run_skopeo(
    *args: str,
    check: bool = ...,
    capture: Literal[True],
    stdin_data: bytes | None = ...,
) -> subprocess.CompletedProcess[bytes]: ...


@overload
def run_skopeo(
    *args: str,
    check: bool = ...,
    capture: Literal[False] = ...,
    stdin_data: bytes | None = ...,
) -> subprocess.CompletedProcess[None]: ...


def run_skopeo(
    *args: str,
    check: bool = True,
    capture: bool = False,
    stdin_data: bytes | None = None,
) -> subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[None]:
    """Run a skopeo command."""
    return run_cmd("skopeo", *args, check=check, capture=capture, stdin_data=stdin_data)  # type: ignore[call-overload, no-any-return]


@overload
def run_oc(
    *args: str,
    check: bool = ...,
    capture: Literal[True],
    stdin_data: bytes | None = ...,
) -> subprocess.CompletedProcess[bytes]: ...


@overload
def run_oc(
    *args: str,
    check: bool = ...,
    capture: Literal[False] = ...,
    stdin_data: bytes | None = ...,
) -> subprocess.CompletedProcess[None]: ...


def run_oc(
    *args: str,
    check: bool = True,
    capture: bool = False,
    stdin_data: bytes | None = None,
) -> subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[None]:
    """Run an oc (OpenShift CLI) command."""
    return run_cmd("oc", *args, check=check, capture=capture, stdin_data=stdin_data)  # type: ignore[call-overload, no-any-return]


def check_tool(name: str) -> bool:
    """Check if an external tool is available on PATH."""
    return shutil.which(name) is not None
