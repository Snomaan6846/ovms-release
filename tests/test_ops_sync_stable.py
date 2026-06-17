"""Tests for ops/sync_stable.py — mocks all tools.* calls."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from ovms_release.context import ReleaseContext
from ovms_release.ops import sync_stable


@pytest.fixture
def ctx() -> ReleaseContext:
    return ReleaseContext(version="2024.3")


class TestTreeTransplant:
    def test_success_no_untracked(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "status" in args and "--porcelain" in args:
                return subprocess.CompletedProcess([], 0, b"M  file.txt\n", b"")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            patch("ovms_release.tools.run_gh") as mock_gh,
        ):
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"https://github.com/org/repo/pull/5\n", b"")
            result = sync_stable.tree_transplant(ctx)
            assert result.success is True
            assert result.pr_url == "https://github.com/org/repo/pull/5"

    def test_untracked_files_need_confirm(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "status" in args and "--porcelain" in args:
                return subprocess.CompletedProcess([], 0, b"?? new_file.txt\n", b"")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with patch("ovms_release.tools.run_git", side_effect=git_side):
            result = sync_stable.tree_transplant(ctx)
            assert result.needs_confirm is True
            assert "new_file.txt" in result.untracked_files

    def test_confirm_clean_second_call(self, ctx: ReleaseContext) -> None:
        git_calls: list[tuple[str, ...]] = []

        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            git_calls.append(args)
            if "status" in args and "--porcelain" in args:
                return subprocess.CompletedProcess([], 0, b"", b"")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            patch("ovms_release.tools.run_gh") as mock_gh,
        ):
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"https://github.com/org/repo/pull/6\n", b"")
            result = sync_stable.tree_transplant(ctx, confirm_clean=True)
            assert result.success is True
            assert any("switch" in c and "sync-stable-2024.3" in c for c in git_calls)
            assert any("clean" in c for c in git_calls)

    def test_dry_run(self, ctx: ReleaseContext) -> None:
        ctx = ReleaseContext(version="2024.3", dry_run=True)

        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "status" in args:
                return subprocess.CompletedProcess([], 0, b"", b"")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with patch("ovms_release.tools.run_git", side_effect=git_side):
            result = sync_stable.tree_transplant(ctx)
            assert result.success is True
            assert result.pr_url == ""

    def test_branch_already_exists(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "switch" in args and "-c" in args:
                raise subprocess.CalledProcessError(1, "git")
            if "status" in args:
                return subprocess.CompletedProcess([], 0, b"", b"")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            patch("ovms_release.tools.run_gh") as mock_gh,
        ):
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"url\n", b"")
            result = sync_stable.tree_transplant(ctx)
            assert result.success is True


class TestVerifySync:
    def test_clean(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "diff" in args:
                return subprocess.CompletedProcess([], 0, b"", b"")
            if "ls-tree" in args:
                return subprocess.CompletedProcess([], 0, b".tekton/pipeline.yaml\n", b"")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with patch("ovms_release.tools.run_git", side_effect=git_side):
            issues = sync_stable.verify_sync(ctx)
            assert issues == []

    def test_content_divergence(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "diff" in args:
                return subprocess.CompletedProcess([], 0, b"src/main.cc\n", b"")
            if "ls-tree" in args:
                return subprocess.CompletedProcess([], 0, b".tekton/p.yaml\n", b"")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with patch("ovms_release.tools.run_git", side_effect=git_side):
            issues = sync_stable.verify_sync(ctx)
            assert len(issues) == 1
            assert "divergence" in issues[0]

    def test_missing_protected(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "diff" in args:
                return subprocess.CompletedProcess([], 0, b"", b"")
            if "ls-tree" in args:
                return subprocess.CompletedProcess([], 0, b"", b"")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with patch("ovms_release.tools.run_git", side_effect=git_side):
            issues = sync_stable.verify_sync(ctx)
            assert any("Protected directories" in i for i in issues)
