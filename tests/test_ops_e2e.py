"""Tests for ops/e2e.py."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from ovms_release.context import ReleaseContext
from ovms_release.ops import e2e


@pytest.fixture
def ctx() -> ReleaseContext:
    return ReleaseContext(version="2024.3")


class TestRunE2E:
    def test_no_runtime(self, ctx: ReleaseContext) -> None:
        with (
            patch("ovms_release.tools.check_tool", return_value=False),
            pytest.raises(e2e.E2EError, match="podman or docker"),
        ):
            e2e.run_e2e(ctx, "quay.io/test/image:latest")

    def test_no_oc(self, ctx: ReleaseContext) -> None:
        def check_side(name: str) -> bool:
            return name == "podman"

        with (
            patch("ovms_release.tools.check_tool", side_effect=check_side),
            pytest.raises(e2e.E2EError, match="oc CLI"),
        ):
            e2e.run_e2e(ctx, "quay.io/test/image:latest")

    def test_missing_aws_env(self, ctx: ReleaseContext, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

        with (
            patch("ovms_release.tools.check_tool", return_value=True),
            pytest.raises(e2e.E2EError, match="AWS_ACCESS_KEY_ID"),
        ):
            e2e.run_e2e(ctx, "quay.io/test/image:latest")

    def test_success(self, ctx: ReleaseContext, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")

        with (
            patch("ovms_release.tools.check_tool", return_value=True),
            patch("ovms_release.tools.run_cmd") as mock_cmd,
        ):
            mock_cmd.return_value = subprocess.CompletedProcess([], 0, None, None)
            e2e.run_e2e(ctx, "quay.io/test/image:latest")
            mock_cmd.assert_called_once()

    def test_smoke_only(self, ctx: ReleaseContext, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")

        with (
            patch("ovms_release.tools.check_tool", return_value=True),
            patch("ovms_release.tools.run_cmd") as mock_cmd,
        ):
            mock_cmd.return_value = subprocess.CompletedProcess([], 0, None, None)
            e2e.run_e2e(ctx, "quay.io/test/image:latest", smoke_only=True)
            call_args = mock_cmd.call_args[0]
            assert "-k" in call_args
            assert "basic" in call_args
