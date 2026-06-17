"""Tests for ops/sync_rhoai.py — mocks all tools.* calls."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from ovms_release.context import EmptySyncError, ReleaseContext
from ovms_release.ops import sync_rhoai


@pytest.fixture
def ctx() -> ReleaseContext:
    return ReleaseContext(version="2024.3", rhoai_version="2.15")


class TestSyncToRhoai:
    def test_success(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "diff" in args and "--cached" in args:
                return subprocess.CompletedProcess([], 0, b" 5 files changed\n", b"")
            if "ls-files" in args:
                return subprocess.CompletedProcess([], 0, b"", b"")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            patch("ovms_release.tools.run_gh") as mock_gh,
        ):
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"https://github.com/org/repo/pull/10\n", b"")
            result = sync_rhoai.sync_to_rhoai(ctx)
            assert result == "https://github.com/org/repo/pull/10"

    def test_empty_sync_raises(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "diff" in args and "--cached" in args:
                return subprocess.CompletedProcess([], 0, b"", b"")
            if "ls-files" in args:
                return subprocess.CompletedProcess([], 0, b"", b"")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            pytest.raises(EmptySyncError, match="no changes"),
        ):
            sync_rhoai.sync_to_rhoai(ctx)

    def test_dry_run(self, ctx: ReleaseContext) -> None:
        ctx = ReleaseContext(version="2024.3", rhoai_version="2.15", dry_run=True)

        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "diff" in args and "--cached" in args:
                return subprocess.CompletedProcess([], 0, b" changes\n", b"")
            if "ls-files" in args:
                return subprocess.CompletedProcess([], 0, b"", b"")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with patch("ovms_release.tools.run_git", side_effect=git_side):
            result = sync_rhoai.sync_to_rhoai(ctx)
            assert result is None

    def test_no_rhoai_version(self) -> None:
        ctx = ReleaseContext(version="2024.3")
        with pytest.raises(ValueError, match="rhoai_version"):
            sync_rhoai.sync_to_rhoai(ctx)

    def test_merge_conflict_handled(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "merge" in args and "--no-commit" in args:
                raise subprocess.CalledProcessError(1, "git")
            if "diff" in args and "--cached" in args:
                return subprocess.CompletedProcess([], 0, b" changes\n", b"")
            if "ls-files" in args:
                return subprocess.CompletedProcess([], 0, b"", b"")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            patch("ovms_release.tools.run_gh") as mock_gh,
        ):
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"url\n", b"")
            result = sync_rhoai.sync_to_rhoai(ctx)
            assert result == "url"

    def test_branch_creation_failure(self, ctx: ReleaseContext) -> None:
        """Branch creation failure raises RuntimeError."""

        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "switch" in args and "-c" in args:
                raise subprocess.CalledProcessError(1, "git")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            pytest.raises(RuntimeError, match="Cannot create branch"),
        ):
            sync_rhoai.sync_to_rhoai(ctx)

    def test_leftover_files_raises(self, ctx: ReleaseContext) -> None:
        """If .tekton or .github/workflows remain tracked after rm, raises RuntimeError."""

        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "ls-files" in args:
                return subprocess.CompletedProcess([], 0, b".tekton/pipeline.yaml\n", b"")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            pytest.raises(RuntimeError, match=r"\.tekton.*still tracked"),
        ):
            sync_rhoai.sync_to_rhoai(ctx)
