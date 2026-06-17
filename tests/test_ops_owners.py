"""Tests for ops/owners.py — mocks all tools.* calls."""

from __future__ import annotations

import subprocess
from unittest.mock import mock_open, patch

import pytest

from ovms_release.context import ReleaseContext
from ovms_release.ops import owners


@pytest.fixture
def ctx() -> ReleaseContext:
    return ReleaseContext(version="2024.3")


class TestPushOwners:
    def test_owners_already_up_to_date(self, ctx: ReleaseContext) -> None:
        with (
            patch("ovms_release.tools.run_git") as mock_git,
            patch("ovms_release.tools.run_gh"),
            patch("builtins.open", mock_open()),
        ):
            mock_git.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            result = owners.push_owners(ctx)
            assert result is None

    def test_creates_pr(self, ctx: ReleaseContext) -> None:
        call_idx = 0

        def git_side_effect(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            nonlocal call_idx
            call_idx += 1
            if "diff" in args and "--quiet" in args:
                raise subprocess.CalledProcessError(1, "git")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side_effect),
            patch("ovms_release.tools.run_gh") as mock_gh,
            patch("builtins.open", mock_open()),
        ):
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"https://github.com/org/repo/pull/42\n", b"")
            result = owners.push_owners(ctx)
            assert result == "https://github.com/org/repo/pull/42"

    def test_dry_run(self, ctx: ReleaseContext) -> None:
        ctx = ReleaseContext(version="2024.3", dry_run=True)

        def git_side_effect(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "diff" in args and "--quiet" in args:
                raise subprocess.CalledProcessError(1, "git")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side_effect),
            patch("ovms_release.tools.run_gh"),
            patch("builtins.open", mock_open()),
        ):
            result = owners.push_owners(ctx)
            assert result is None

    def test_branch_already_exists(self, ctx: ReleaseContext) -> None:
        call_idx = 0

        def git_side_effect(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            nonlocal call_idx
            call_idx += 1
            if "switch" in args and "-c" in args:
                raise subprocess.CalledProcessError(1, "git")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side_effect),
            patch("ovms_release.tools.run_gh"),
            patch("builtins.open", mock_open()),
        ):
            result = owners.push_owners(ctx)
            assert result is None
