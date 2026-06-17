"""Tests for ops/rebuild.py."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from ovms_release.context import ReleaseContext
from ovms_release.ops import rebuild


@pytest.fixture
def ctx() -> ReleaseContext:
    return ReleaseContext(version="2024.3")


class TestCveRebuild:
    def test_empty_commit(self, ctx: ReleaseContext) -> None:
        with (
            patch("ovms_release.tools.run_git") as mock_git,
            patch("ovms_release.tools.run_gh") as mock_gh,
            patch("ovms_release.tools.run_cmd"),
        ):
            mock_git.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"url\n", b"")
            result = rebuild.cve_rebuild(ctx, "2024.3-release")
            assert result == "url"

    def test_bump_base(self, ctx: ReleaseContext) -> None:
        with (
            patch("ovms_release.tools.run_git") as mock_git,
            patch("ovms_release.tools.run_gh") as mock_gh,
            patch("ovms_release.tools.run_cmd") as mock_cmd,
        ):
            mock_git.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"url\n", b"")
            mock_cmd.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            result = rebuild.cve_rebuild(ctx, "2024.3-release", bump_base=True)
            assert result == "url"

    def test_dry_run(self, ctx: ReleaseContext) -> None:
        ctx = ReleaseContext(version="2024.3", dry_run=True)
        with (
            patch("ovms_release.tools.run_git") as mock_git,
            patch("ovms_release.tools.run_cmd"),
        ):
            mock_git.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            assert rebuild.cve_rebuild(ctx, "2024.3-release") is None

    def test_rhoai_branch(self, ctx: ReleaseContext) -> None:
        with (
            patch("ovms_release.tools.run_git") as mock_git,
            patch("ovms_release.tools.run_gh") as mock_gh,
            patch("ovms_release.tools.run_cmd"),
        ):
            mock_git.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"url\n", b"")
            rebuild.cve_rebuild(ctx, "rhoai-2.15")
