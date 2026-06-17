"""Tests for ops/diff_args.py — mocks all tools.* calls."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from ovms_release.context import ReleaseContext
from ovms_release.ops import diff_args


@pytest.fixture
def ctx() -> ReleaseContext:
    return ReleaseContext(version="2024.3")


OLD_DOCKERFILE = b"""\
FROM ubi9
ARG OV_VERSION=2024.2.0
ARG PYTHON=python3.11
ARG OLD_ONLY=removed_val
RUN echo hello
"""

NEW_DOCKERFILE = b"""\
FROM ubi9
ARG OV_VERSION=2024.3.0
ARG PYTHON=python3.11
ARG NEW_ARG=new_val
RUN echo hello
"""


class TestDiffArgs:
    def test_detects_changes(self, ctx: ReleaseContext) -> None:
        def git_side_effect(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            ref = args[1] if len(args) > 1 else ""
            if "2024.2-release" in ref:
                return subprocess.CompletedProcess(list(args), 0, OLD_DOCKERFILE, b"")
            return subprocess.CompletedProcess(list(args), 0, NEW_DOCKERFILE, b"")

        with patch("ovms_release.tools.run_git", side_effect=git_side_effect):
            result = diff_args.diff_args(ctx)
            assert "NEW_ARG" in result.added
            assert result.added["NEW_ARG"] == "new_val"
            assert "OLD_ONLY" in result.removed
            assert "OV_VERSION" in result.changed
            assert result.changed["OV_VERSION"] == ("2024.2.0", "2024.3.0")
            assert "PYTHON" not in result.changed

    def test_no_changes(self, ctx: ReleaseContext) -> None:
        with patch("ovms_release.tools.run_git") as mock_git:
            mock_git.return_value = subprocess.CompletedProcess([], 0, b"ARG FOO=bar\nARG BAZ=qux\n", b"")
            result = diff_args.diff_args(ctx)
            assert result.added == {}
            assert result.removed == {}
            assert result.changed == {}

    def test_old_branch_missing(self, ctx: ReleaseContext) -> None:
        def git_side_effect(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            ref = args[1] if len(args) > 1 else ""
            if "2024.2-release" in ref:
                raise subprocess.CalledProcessError(1, "git")
            return subprocess.CompletedProcess(list(args), 0, NEW_DOCKERFILE, b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side_effect),
            pytest.raises(diff_args.ArgDiffError, match=r"2024\.2-release"),
        ):
            diff_args.diff_args(ctx)

    def test_new_branch_missing(self, ctx: ReleaseContext) -> None:
        def git_side_effect(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            ref = args[1] if len(args) > 1 else ""
            if "2024.3-release" in ref:
                raise subprocess.CalledProcessError(1, "git")
            return subprocess.CompletedProcess(list(args), 0, OLD_DOCKERFILE, b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side_effect),
            pytest.raises(diff_args.ArgDiffError, match=r"2024\.3-release"),
        ):
            diff_args.diff_args(ctx)

    def test_explicit_old_version(self, ctx: ReleaseContext) -> None:
        with patch("ovms_release.tools.run_git") as mock_git:
            mock_git.return_value = subprocess.CompletedProcess([], 0, b"ARG X=1\n", b"")
            result = diff_args.diff_args(ctx, old_version="2023.6")
            assert result.added == {}
            calls = [str(c) for c in mock_git.call_args_list]
            assert any("2023.6-release" in c for c in calls)

    def test_arg_without_value(self, ctx: ReleaseContext) -> None:
        with patch("ovms_release.tools.run_git") as mock_git:
            mock_git.return_value = subprocess.CompletedProcess([], 0, b"ARG NOVALUE\nARG WITH=val\n", b"")
            result = diff_args.diff_args(ctx)
            assert result.added == {}
