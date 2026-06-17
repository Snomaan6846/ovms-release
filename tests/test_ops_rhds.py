"""Tests for ops/rhds.py."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from ovms_release.context import ReleaseContext
from ovms_release.ops import rhds


@pytest.fixture
def ctx() -> ReleaseContext:
    return ReleaseContext(version="2024.3", rhoai_version="2.15")


class TestCheckRhdsSync:
    def test_in_sync(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "rev-list" in args:
                return subprocess.CompletedProcess([], 0, b"0\n", b"")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with patch("ovms_release.tools.run_git", side_effect=git_side):
            result = rhds.check_rhds_sync(ctx)
            assert result["rhoai-2.15"] == "in_sync"

    def test_behind(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "rev-list" in args:
                return subprocess.CompletedProcess([], 0, b"3\n", b"")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with patch("ovms_release.tools.run_git", side_effect=git_side):
            result = rhds.check_rhds_sync(ctx)
            assert result["rhoai-2.15"] == "behind_by_3"

    def test_no_rhoai_version(self) -> None:
        ctx = ReleaseContext(version="2024.3")
        result = rhds.check_rhds_sync(ctx)
        assert "error" in result

    def test_fetch_fails(self, ctx: ReleaseContext) -> None:
        with patch(
            "ovms_release.tools.run_git",
            side_effect=subprocess.CalledProcessError(1, "git"),
        ):
            result = rhds.check_rhds_sync(ctx)
            assert "fetch_failed" in result.values()
