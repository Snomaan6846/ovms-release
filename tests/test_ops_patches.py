"""Tests for ops/patches.py — mocks all tools.* calls."""

from __future__ import annotations

import subprocess
from typing import Any
from unittest.mock import patch

import pytest

from ovms_release.context import ReleaseContext
from ovms_release.ops import patches


@pytest.fixture
def ctx() -> ReleaseContext:
    return ReleaseContext(version="2024.3")


class TestCheckPatches:
    def test_all_apply(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            if "ls-tree" in args:
                return subprocess.CompletedProcess([], 0, b"01-fix.patch\n02-fix.patch\n", b"")
            return subprocess.CompletedProcess(list(args), 0, b"patch-data", b"")

        with patch("ovms_release.tools.run_git", side_effect=git_side):
            result = patches.check_patches(ctx)
            assert result == {"01-fix.patch": True, "02-fix.patch": True}

    def test_one_fails(self, ctx: ReleaseContext) -> None:
        call_count = 0

        def git_side(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            nonlocal call_count
            call_count += 1
            if "ls-tree" in args:
                return subprocess.CompletedProcess([], 0, b"01-fix.patch\n", b"")
            if "apply" in args:
                raise subprocess.CalledProcessError(1, "git")
            return subprocess.CompletedProcess(list(args), 0, b"patch-data", b"")

        with patch("ovms_release.tools.run_git", side_effect=git_side):
            result = patches.check_patches(ctx)
            assert result == {"01-fix.patch": False}


class TestApplyPatches:
    def test_success(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            if "ls-tree" in args:
                return subprocess.CompletedProcess([], 0, b"01-fix.patch\n", b"")
            return subprocess.CompletedProcess(list(args), 0, b"patch-data", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            patch("ovms_release.tools.run_gh") as mock_gh,
        ):
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"https://github.com/org/repo/pull/1\n", b"")
            result = patches.apply_patches(ctx)
            assert result == "https://github.com/org/repo/pull/1"

    def test_dry_run(self, ctx: ReleaseContext) -> None:
        ctx = ReleaseContext(version="2024.3", dry_run=True)

        def git_side(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            if "ls-tree" in args:
                return subprocess.CompletedProcess([], 0, b"01-fix.patch\n", b"")
            return subprocess.CompletedProcess(list(args), 0, b"patch-data", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            patch("ovms_release.tools.run_gh"),
        ):
            result = patches.apply_patches(ctx)
            assert result is None

    def test_branch_creation_failure(self, ctx: ReleaseContext) -> None:
        """Branch creation failure raises PatchError."""

        def git_side(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            if "switch" in args and "-c" in args:
                raise subprocess.CalledProcessError(1, "git")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            pytest.raises(patches.PatchError, match="Cannot create branch"),
        ):
            patches.apply_patches(ctx)

    def test_non_04_apply_failure(self, ctx: ReleaseContext) -> None:
        """Non-04 patch apply failure is counted and raises PatchError."""

        def git_side(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            if "ls-tree" in args:
                return subprocess.CompletedProcess([], 0, b"01-fix.patch\n02-fix.patch\n", b"")
            if "apply" in args and "--check" not in args and "-" in args:
                raise subprocess.CalledProcessError(1, "git")
            return subprocess.CompletedProcess(list(args), 0, b"patch-data", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            pytest.raises(patches.PatchError, match="2 patch"),
        ):
            patches.apply_patches(ctx)

    def test_no_patches(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            if "ls-tree" in args:
                return subprocess.CompletedProcess([], 0, b"", b"")
            return subprocess.CompletedProcess(list(args), 0, b"", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            pytest.raises(patches.PatchError, match="No patches"),
        ):
            patches.apply_patches(ctx)

    def test_check_fails(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            if "ls-tree" in args:
                return subprocess.CompletedProcess([], 0, b"01-fix.patch\n", b"")
            if "apply" in args and "--check" in args:
                raise subprocess.CalledProcessError(1, "git")
            return subprocess.CompletedProcess(list(args), 0, b"patch-data", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            pytest.raises(patches.PatchError, match="1 patch"),
        ):
            patches.apply_patches(ctx)

    def test_04_patches_skip_precheck(self, ctx: ReleaseContext) -> None:
        """04- patches are excluded from pre-validation since they target Dockerfile.konflux."""

        def git_side(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            if "ls-tree" in args:
                return subprocess.CompletedProcess([], 0, b"01-fix.patch\n04-labels.patch\n", b"")
            if "apply" in args and "--check" in args:
                data = kwargs.get("stdin_data", b"")
                if b"04-labels" in data:
                    raise AssertionError("04- patches must not be pre-validated")
            return subprocess.CompletedProcess(list(args), 0, b"patch-data", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            patch("ovms_release.tools.run_gh") as mock_gh,
        ):
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"https://github.com/org/repo/pull/99\n", b"")
            result = patches.apply_patches(ctx)
            assert result == "https://github.com/org/repo/pull/99"

    def test_04_patches_applied_after_regular(self, ctx: ReleaseContext) -> None:
        """04- patches are applied in the second pass (after Dockerfile.konflux exists)."""
        apply_order: list[str] = []

        def git_side(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            if "ls-tree" in args:
                return subprocess.CompletedProcess([], 0, b"01-build.patch\n04-labels.patch\n", b"")
            if "apply" in args and "--check" not in args and "-" in args:
                data = kwargs.get("stdin_data", b"")
                if b"01-build" in data:
                    apply_order.append("01-build.patch")
                elif b"04-labels" in data:
                    apply_order.append("04-labels.patch")
            if "show" in args:
                ref = args[1] if len(args) > 1 else ""
                if "01-build" in ref:
                    return subprocess.CompletedProcess([], 0, b"01-build content", b"")
                if "04-labels" in ref:
                    return subprocess.CompletedProcess([], 0, b"04-labels content", b"")
            return subprocess.CompletedProcess(list(args), 0, b"ok", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            patch("ovms_release.tools.run_gh") as mock_gh,
        ):
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"url\n", b"")
            patches.apply_patches(ctx)
            assert apply_order == ["01-build.patch", "04-labels.patch"]

    def test_apply_failure_in_04_raises(self, ctx: ReleaseContext) -> None:
        """04- patch application failure is counted and raises PatchError."""

        def git_side(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            if "ls-tree" in args:
                return subprocess.CompletedProcess([], 0, b"04-labels.patch\n", b"")
            if "apply" in args and "--check" not in args and "-" in args:
                raise subprocess.CalledProcessError(1, "git")
            return subprocess.CompletedProcess(list(args), 0, b"data", b"")

        with (
            patch("ovms_release.tools.run_git", side_effect=git_side),
            pytest.raises(patches.PatchError, match="1 patch"),
        ):
            patches.apply_patches(ctx)


class TestDiagnosePatches:
    def test_all_ok(self, ctx: ReleaseContext) -> None:
        def git_side(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            if "ls-tree" in args:
                return subprocess.CompletedProcess([], 0, b"01-fix.patch\n", b"")
            return subprocess.CompletedProcess(list(args), 0, b"patch-data", b"")

        with patch("ovms_release.tools.run_git", side_effect=git_side):
            assert patches.diagnose_patches(ctx) == {}

    def test_failures_with_captured_stderr(self, ctx: ReleaseContext) -> None:
        """Verifies capture=True enables proper error message extraction."""

        def git_side(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            if "ls-tree" in args:
                return subprocess.CompletedProcess([], 0, b"01-fix.patch\n", b"")
            if "apply" in args and "--check" in args:
                err = subprocess.CalledProcessError(1, "git")
                err.stderr = b"error: patch failed: src/file.c:42\nhunk 1/1 FAILED\n"
                raise err
            return subprocess.CompletedProcess(list(args), 0, b"patch-data", b"")

        with patch("ovms_release.tools.run_git", side_effect=git_side):
            failures = patches.diagnose_patches(ctx)
            assert "01-fix.patch" in failures
            assert "patch failed" in failures["01-fix.patch"]

    def test_failures_without_stderr_fallback(self, ctx: ReleaseContext) -> None:
        """When stderr is None (shouldn't happen with capture=True, but defensive), returns unknown."""

        def git_side(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            if "ls-tree" in args:
                return subprocess.CompletedProcess([], 0, b"01-fix.patch\n", b"")
            if "apply" in args:
                err = subprocess.CalledProcessError(1, "git")
                err.stderr = None
                raise err
            return subprocess.CompletedProcess(list(args), 0, b"patch-data", b"")

        with patch("ovms_release.tools.run_git", side_effect=git_side):
            failures = patches.diagnose_patches(ctx)
            assert failures["01-fix.patch"] == "unknown error"

    def test_diagnose_uses_capture_true(self, ctx: ReleaseContext) -> None:
        """Ensure diagnose_patches passes capture=True to git apply --check."""
        calls_with_capture: list[bool] = []

        def git_side(*args: str, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
            if "ls-tree" in args:
                return subprocess.CompletedProcess([], 0, b"01-fix.patch\n", b"")
            if "apply" in args and "--check" in args:
                calls_with_capture.append(kwargs.get("capture", False))
            return subprocess.CompletedProcess(list(args), 0, b"patch-data", b"")

        with patch("ovms_release.tools.run_git", side_effect=git_side):
            patches.diagnose_patches(ctx)
            assert calls_with_capture == [True]
