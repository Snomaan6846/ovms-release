"""Tests for ops/jira.py."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from ovms_release.context import ReleaseContext
from ovms_release.ops import jira


@pytest.fixture
def ctx() -> ReleaseContext:
    return ReleaseContext(version="2024.3")


class TestTransitionIssue:
    def test_with_acli(self, ctx: ReleaseContext) -> None:
        with (
            patch("ovms_release.tools.check_tool", return_value=True),
            patch("ovms_release.tools.run_cmd") as mock_cmd,
        ):
            mock_cmd.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            assert jira.transition_issue(ctx, "RHOAIENG-123", "In Progress") is True

    def test_acli_fails(self, ctx: ReleaseContext) -> None:
        with (
            patch("ovms_release.tools.check_tool", return_value=True),
            patch("ovms_release.tools.run_cmd", side_effect=subprocess.CalledProcessError(1, "acli")),
        ):
            assert jira.transition_issue(ctx, "RHOAIENG-123", "Done") is False

    def test_no_backend(self, ctx: ReleaseContext, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("JIRA_API_TOKEN", raising=False)
        monkeypatch.delenv("JIRA_USER_EMAIL", raising=False)

        with patch("ovms_release.tools.check_tool", return_value=False):
            assert jira.transition_issue(ctx, "RHOAIENG-123", "Done") is False

    def test_rest_token_present(self, ctx: ReleaseContext, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JIRA_API_TOKEN", "tok")
        monkeypatch.setenv("JIRA_USER_EMAIL", "me@x.com")

        with patch("ovms_release.tools.check_tool", return_value=False):
            assert jira.transition_issue(ctx, "RHOAIENG-123", "Done") is False


class TestAddComment:
    def test_with_acli(self, ctx: ReleaseContext) -> None:
        with (
            patch("ovms_release.tools.check_tool", return_value=True),
            patch("ovms_release.tools.run_cmd") as mock_cmd,
        ):
            mock_cmd.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            assert jira.add_comment(ctx, "KEY-1", "hello") is True

    def test_acli_fails(self, ctx: ReleaseContext) -> None:
        with (
            patch("ovms_release.tools.check_tool", return_value=True),
            patch("ovms_release.tools.run_cmd", side_effect=subprocess.CalledProcessError(1, "acli")),
        ):
            assert jira.add_comment(ctx, "KEY-1", "oops") is False

    def test_no_acli(self, ctx: ReleaseContext) -> None:
        with patch("ovms_release.tools.check_tool", return_value=False):
            assert jira.add_comment(ctx, "KEY-1", "nope") is False


class TestCreateReleaseIssue:
    def test_success(self, ctx: ReleaseContext) -> None:
        with (
            patch("ovms_release.tools.check_tool", return_value=True),
            patch("ovms_release.tools.run_cmd") as mock_cmd,
        ):
            mock_cmd.return_value = subprocess.CompletedProcess([], 0, b"RHOAIENG-456\n", b"")
            assert jira.create_release_issue(ctx) == "RHOAIENG-456"

    def test_no_acli(self, ctx: ReleaseContext) -> None:
        with patch("ovms_release.tools.check_tool", return_value=False):
            assert jira.create_release_issue(ctx) is None
