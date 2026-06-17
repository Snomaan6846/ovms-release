"""Tests for ops/mirror.py — mocks all tools.* calls."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from ovms_release.context import ReleaseContext
from ovms_release.ops import mirror


@pytest.fixture
def ctx() -> ReleaseContext:
    return ReleaseContext(version="2024.3")


class TestMirrorBranches:
    def test_validate_only(self, ctx: ReleaseContext) -> None:
        with patch("ovms_release.tools.run_gh") as mock_gh:
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"abc123def456\n", b"")
            results = mirror.mirror_branches(ctx, validate_only=True)
            assert all(v == "validated" for v in results.values())
            assert len(results) == 4

    def test_upstream_missing(self, ctx: ReleaseContext) -> None:
        with (
            patch(
                "ovms_release.tools.run_gh",
                side_effect=subprocess.CalledProcessError(1, "gh"),
            ),
            pytest.raises(mirror.MirrorError, match="4 repo"),
        ):
            mirror.mirror_branches(ctx)

    def test_already_exists(self, ctx: ReleaseContext) -> None:
        call_count = 0

        def gh_side_effect(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            nonlocal call_count
            call_count += 1
            return subprocess.CompletedProcess(list(args), 0, b"sha123\n", b"")

        with patch("ovms_release.tools.run_gh", side_effect=gh_side_effect):
            results = mirror.mirror_branches(ctx)
            assert all(v == "already_exists" for v in results.values())

    def test_dry_run(self, ctx: ReleaseContext) -> None:
        ctx = ReleaseContext(version="2024.3", dry_run=True)
        call_count = 0

        def gh_side_effect(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            nonlocal call_count
            call_count += 1
            if ("git/ref/heads" in args[1] if len(args) > 1 else False) and call_count % 2 == 0:
                raise subprocess.CalledProcessError(1, "gh")
            return subprocess.CompletedProcess(list(args), 0, b"sha123\n", b"")

        with patch("ovms_release.tools.run_gh", side_effect=gh_side_effect):
            results = mirror.mirror_branches(ctx)
            assert "dry_run" in results.values() or "already_exists" in results.values()

    def test_create_success(self, ctx: ReleaseContext) -> None:
        calls: list[tuple[str, ...]] = []

        def gh_side_effect(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            calls.append(args)
            url = args[1] if len(args) > 1 else ""
            if "/git/ref/heads/" in url and "openvinotoolkit" not in url:
                raise subprocess.CalledProcessError(1, "gh")
            return subprocess.CompletedProcess(list(args), 0, b"sha123\n", b"")

        with patch("ovms_release.tools.run_gh", side_effect=gh_side_effect):
            results = mirror.mirror_branches(ctx)
            assert "created" in results.values()

    def test_create_fails(self, ctx: ReleaseContext) -> None:
        call_count = 0

        def gh_side_effect(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            nonlocal call_count
            call_count += 1
            url = args[1] if len(args) > 1 else ""
            if "/git/ref/heads/" in url and "openvinotoolkit" not in url:
                raise subprocess.CalledProcessError(1, "gh")
            if "/git/refs" in url:
                raise subprocess.CalledProcessError(1, "gh")
            return subprocess.CompletedProcess(list(args), 0, b"sha123\n", b"")

        with (
            patch("ovms_release.tools.run_gh", side_effect=gh_side_effect),
            pytest.raises(mirror.MirrorError),
        ):
            mirror.mirror_branches(ctx)


class TestHelpers:
    def test_get_midstream_branch_ovms(self) -> None:
        assert mirror._get_midstream_branch("openvino_model_server", "2024", "3") == "2024.3-release"

    def test_get_midstream_branch_other(self) -> None:
        assert mirror._get_midstream_branch("openvino", "2024", "3") == "releases/2024/3"
