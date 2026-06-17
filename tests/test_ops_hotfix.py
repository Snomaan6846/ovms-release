"""Tests for ops/hotfix.py."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from ovms_release.context import ReleaseContext
from ovms_release.ops import hotfix


@pytest.fixture
def ctx() -> ReleaseContext:
    return ReleaseContext(version="2024.3")


class TestCherryPick:
    def test_success(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "merge-base" in args:
                raise subprocess.CalledProcessError(1, "git")
            return subprocess.CompletedProcess(list(args), 0, b"abc123\n", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            patch("ovms_release.tools.run_gh") as mock_gh,
        ):
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"url\n", b"")
            result = hotfix.cherry_pick(ctx, "abc123def", "2024.3-release")
            assert result == "url"

    def test_already_ancestor(self, ctx: ReleaseContext) -> None:
        with patch("ovms_release.tools.run_git") as mock_git:
            mock_git.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            result = hotfix.cherry_pick(ctx, "abc123", "2024.3-release")
            assert result is None

    def test_commit_not_found(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "show" in args:
                raise subprocess.CalledProcessError(1, "git")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            pytest.raises(hotfix.HotfixError, match="not found"),
        ):
            hotfix.cherry_pick(ctx, "deadbeef", "2024.3-release")

    def test_rhoai_target(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "merge-base" in args:
                raise subprocess.CalledProcessError(1, "git")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            patch("ovms_release.tools.run_gh") as mock_gh,
        ):
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"url\n", b"")
            result = hotfix.cherry_pick(ctx, "abc123", "rhoai-2.15")
            assert result == "url"
