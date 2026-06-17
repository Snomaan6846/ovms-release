"""Tests for ops/preflight.py — mocks all tools.* calls."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from ovms_release.context import ReleaseContext
from ovms_release.ops import preflight


@pytest.fixture
def ctx() -> ReleaseContext:
    return ReleaseContext(version="2024.3")


class TestCheckPrerequisites:
    def test_all_ok(self, ctx: ReleaseContext) -> None:
        with (
            patch("ovms_release.tools.check_tool", return_value=True),
            patch("ovms_release.tools.run_gh") as mock_gh,
            patch("ovms_release.tools.run_git") as mock_git,
        ):
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            mock_git.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            errors = preflight.check_prerequisites(ctx)
            assert errors == []

    def test_missing_tool(self, ctx: ReleaseContext) -> None:
        def fake_check_tool(name: str) -> bool:
            return name != "git"

        with (
            patch("ovms_release.tools.check_tool", side_effect=fake_check_tool),
            patch("ovms_release.tools.run_gh") as mock_gh,
            patch("ovms_release.tools.run_git") as mock_git,
        ):
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            mock_git.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            errors = preflight.check_prerequisites(ctx)
            assert any("git" in e for e in errors)

    def test_gh_not_authenticated(self, ctx: ReleaseContext) -> None:
        with (
            patch("ovms_release.tools.check_tool", return_value=True),
            patch(
                "ovms_release.tools.run_gh",
                side_effect=subprocess.CalledProcessError(1, "gh"),
            ),
            patch("ovms_release.tools.run_git") as mock_git,
        ):
            mock_git.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            errors = preflight.check_prerequisites(ctx)
            assert any("gh not authenticated" in e for e in errors)

    def test_missing_remote(self, ctx: ReleaseContext) -> None:
        def git_side_effect(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if "remote" in args and "downstream" in args:
                raise subprocess.CalledProcessError(1, "git")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with (
            patch("ovms_release.tools.check_tool", return_value=True),
            patch("ovms_release.tools.run_gh") as mock_gh,
            patch("ovms_release.tools.run_git", side_effect=git_side_effect),
        ):
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            errors = preflight.check_prerequisites(ctx)
            assert any("downstream" in e for e in errors)

    def test_e2e_enabled_missing_container(self, ctx: ReleaseContext, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("E2E_ENABLED", "true")

        def fake_check_tool(name: str) -> bool:
            return name not in ("podman", "docker", "oc")

        with (
            patch("ovms_release.tools.check_tool", side_effect=fake_check_tool),
            patch("ovms_release.tools.run_gh") as mock_gh,
            patch("ovms_release.tools.run_git") as mock_git,
        ):
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            mock_git.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            errors = preflight.check_prerequisites(ctx)
            assert any("podman or docker" in e for e in errors)
            assert any("oc" in e for e in errors)


class TestDetectUpstreamReleases:
    def test_finds_new_releases(self) -> None:
        with patch("ovms_release.tools.run_gh") as mock_gh:
            mock_gh.side_effect = [
                subprocess.CompletedProcess(
                    [],
                    0,
                    b"releases/2024/3\nreleases/2024/4\nmain\n",
                    b"",
                ),
                subprocess.CompletedProcess(
                    [],
                    0,
                    b"2024.3-release\nmain\n",
                    b"",
                ),
            ]
            result = preflight.detect_upstream_releases()
            assert "2024.4" in result
            assert "2024.3" not in result

    def test_all_mirrored(self) -> None:
        with patch("ovms_release.tools.run_gh") as mock_gh:
            mock_gh.side_effect = [
                subprocess.CompletedProcess([], 0, b"releases/2024/3\n", b""),
                subprocess.CompletedProcess([], 0, b"2024.3-release\n", b""),
            ]
            result = preflight.detect_upstream_releases()
            assert result == []


class TestCheckUpstreamBranches:
    def test_mixed_results(self, ctx: ReleaseContext) -> None:
        call_count = 0

        def gh_side_effect(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise subprocess.CalledProcessError(1, "gh")
            return subprocess.CompletedProcess(list(args), 0, b"branch_name", b"")

        with patch("ovms_release.tools.run_gh", side_effect=gh_side_effect):
            results = preflight.check_upstream_branches(ctx)
            assert results["model_server"] is True
            assert results["openvino"] is False


class TestCheckMidstreamBranch:
    def test_exists(self, ctx: ReleaseContext) -> None:
        with patch("ovms_release.tools.run_gh") as mock_gh:
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"branch", b"")
            assert preflight.check_midstream_branch(ctx) is True

    def test_not_exists(self, ctx: ReleaseContext) -> None:
        with patch(
            "ovms_release.tools.run_gh",
            side_effect=subprocess.CalledProcessError(1, "gh"),
        ):
            assert preflight.check_midstream_branch(ctx) is False


class TestCheckPatchHealth:
    def test_patches_apply(self, ctx: ReleaseContext) -> None:
        call_idx = 0

        def git_side_effect(*args: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            nonlocal call_idx
            call_idx += 1
            if "ls-tree" in args:
                return subprocess.CompletedProcess(list(args), 0, b"fix1.patch\nfix2.patch\n", b"")
            if "show" in args:
                return subprocess.CompletedProcess(list(args), 0, b"patch-data", b"")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with patch("ovms_release.tools.run_git", side_effect=git_side_effect):
            results = preflight.check_patch_health(ctx)
            assert results == {"fix1.patch": True, "fix2.patch": True}

    def test_fetch_fails(self, ctx: ReleaseContext) -> None:
        with patch(
            "ovms_release.tools.run_git",
            side_effect=subprocess.CalledProcessError(1, "git"),
        ):
            assert preflight.check_patch_health(ctx) == {}


class TestCheckUbiTags:
    def test_with_skopeo(self) -> None:
        import json

        tags_json = json.dumps({"Tags": ["9.4-1234", "9.3-1111", "latest", "9.2-999"]})

        with (
            patch("ovms_release.tools.check_tool", return_value=True),
            patch("ovms_release.tools.run_cmd") as mock_cmd,
        ):
            mock_cmd.return_value = subprocess.CompletedProcess([], 0, tags_json.encode(), b"")
            tags = preflight.check_ubi_tags()
            assert len(tags) <= 5
            assert all("-" in t for t in tags)

    def test_no_skopeo(self) -> None:
        with patch("ovms_release.tools.check_tool", return_value=False):
            assert preflight.check_ubi_tags() == []


class TestCheckForkHealth:
    def test_up_to_date(self, ctx: ReleaseContext) -> None:
        with patch("ovms_release.tools.run_git") as mock_git:
            mock_git.return_value = subprocess.CompletedProcess([], 0, b"0\n", b"")
            assert preflight.check_fork_health(ctx) == 0

    def test_behind(self, ctx: ReleaseContext) -> None:
        with patch("ovms_release.tools.run_git") as mock_git:
            mock_git.return_value = subprocess.CompletedProcess([], 0, b"5\n", b"")
            assert preflight.check_fork_health(ctx) == 5

    def test_unknown(self, ctx: ReleaseContext) -> None:
        with patch(
            "ovms_release.tools.run_git",
            side_effect=subprocess.CalledProcessError(1, "git"),
        ):
            assert preflight.check_fork_health(ctx) is None


class TestRunPreflight:
    def test_raises_on_errors(self, ctx: ReleaseContext) -> None:
        with (
            patch(
                "ovms_release.ops.preflight.check_prerequisites",
                return_value=["git — not found"],
            ),
            pytest.raises(preflight.PreflightError, match="1 prerequisite"),
        ):
            preflight.run_preflight(ctx)

    def test_passes_when_clean(self, ctx: ReleaseContext) -> None:
        with patch(
            "ovms_release.ops.preflight.check_prerequisites",
            return_value=[],
        ):
            preflight.run_preflight(ctx)
