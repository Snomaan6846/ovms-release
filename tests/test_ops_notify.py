"""Tests for ops/notify.py."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from ovms_release.context import ReleaseContext
from ovms_release.ops import notify


@pytest.fixture
def ctx() -> ReleaseContext:
    return ReleaseContext(version="2024.3")


class TestSendNotification:
    def test_no_webhook(self, ctx: ReleaseContext, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NOTIFICATION_WEBHOOK", raising=False)
        assert notify.send_notification(ctx, "test", "hello") is False

    def test_with_webhook(self, ctx: ReleaseContext, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NOTIFICATION_WEBHOOK", "https://hooks.example.com/test")
        with patch("ovms_release.tools.run_cmd") as mock_cmd:
            mock_cmd.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            assert notify.send_notification(ctx, "phase_complete", "Phase 1 done") is True

    def test_explicit_url(self, ctx: ReleaseContext) -> None:
        with patch("ovms_release.tools.run_cmd") as mock_cmd:
            mock_cmd.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            result = notify.send_notification(ctx, "test", "msg", webhook_url="https://example.com/hook")
            assert result is True

    def test_curl_fails(self, ctx: ReleaseContext, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NOTIFICATION_WEBHOOK", "https://hooks.example.com/test")
        with patch(
            "ovms_release.tools.run_cmd",
            side_effect=subprocess.CalledProcessError(1, "curl"),
        ):
            assert notify.send_notification(ctx, "test", "msg") is False
