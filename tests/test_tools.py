"""Tests for tools.py — verifies subprocess wrapper logic."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from ovms_release import tools


class TestRunCmd:
    def test_capture_true_returns_bytes(self) -> None:
        with patch("ovms_release.tools.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(["echo", "hi"], 0, stdout=b"hi\n", stderr=b"")
            result = tools.run_cmd("echo", "hi", capture=True)
            assert result.stdout == b"hi\n"
            mock_run.assert_called_once_with(["echo", "hi"], check=True, capture_output=True, input=None)

    def test_capture_false_returns_none_stdout(self) -> None:
        with patch("ovms_release.tools.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(["echo", "hi"], 0, stdout=None, stderr=None)
            result = tools.run_cmd("echo", "hi", capture=False)
            assert result.stdout is None
            mock_run.assert_called_once_with(["echo", "hi"], check=True, input=None)

    def test_check_false_no_exception(self) -> None:
        with patch("ovms_release.tools.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(["false"], 1)
            result = tools.run_cmd("false", check=False)
            assert result.returncode == 1

    def test_check_true_raises(self) -> None:
        with (
            patch(
                "ovms_release.tools.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "bad"),
            ),
            pytest.raises(subprocess.CalledProcessError),
        ):
            tools.run_cmd("bad", check=True, capture=True)

    def test_stdin_data_passed(self) -> None:
        with patch("ovms_release.tools.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(["cat"], 0, stdout=b"data", stderr=b"")
            tools.run_cmd("cat", capture=True, stdin_data=b"data")
            mock_run.assert_called_once_with(["cat"], check=True, capture_output=True, input=b"data")


class TestRunGit:
    def test_delegates_to_run_cmd(self) -> None:
        with patch("ovms_release.tools.run_cmd") as mock_cmd:
            mock_cmd.return_value = subprocess.CompletedProcess(["git", "status"], 0, stdout=b"clean", stderr=b"")
            result = tools.run_git("status", capture=True)
            mock_cmd.assert_called_once_with("git", "status", check=True, capture=True, stdin_data=None)
            assert result.stdout == b"clean"

    def test_capture_false(self) -> None:
        with patch("ovms_release.tools.run_cmd") as mock_cmd:
            mock_cmd.return_value = subprocess.CompletedProcess(["git", "push"], 0)
            tools.run_git("push", capture=False)
            mock_cmd.assert_called_once_with("git", "push", check=True, capture=False, stdin_data=None)


class TestRunGh:
    def test_delegates(self) -> None:
        with patch("ovms_release.tools.run_cmd") as mock_cmd:
            mock_cmd.return_value = subprocess.CompletedProcess(["gh", "pr", "list"], 0, stdout=b"[]", stderr=b"")
            result = tools.run_gh("pr", "list", capture=True)
            mock_cmd.assert_called_once_with("gh", "pr", "list", check=True, capture=True, stdin_data=None)
            assert result.stdout == b"[]"


class TestRunSkopeo:
    def test_delegates(self) -> None:
        with patch("ovms_release.tools.run_cmd") as mock_cmd:
            mock_cmd.return_value = subprocess.CompletedProcess(["skopeo", "inspect"], 0, stdout=b"{}", stderr=b"")
            result = tools.run_skopeo("inspect", "docker://img", capture=True)
            mock_cmd.assert_called_once_with(
                "skopeo", "inspect", "docker://img", check=True, capture=True, stdin_data=None
            )
            assert result.stdout == b"{}"


class TestRunOc:
    def test_delegates(self) -> None:
        with patch("ovms_release.tools.run_cmd") as mock_cmd:
            mock_cmd.return_value = subprocess.CompletedProcess(["oc", "whoami"], 0, stdout=b"admin", stderr=b"")
            result = tools.run_oc("whoami", capture=True)
            mock_cmd.assert_called_once_with("oc", "whoami", check=True, capture=True, stdin_data=None)
            assert result.stdout == b"admin"


class TestCheckTool:
    def test_found(self) -> None:
        with patch("ovms_release.tools.shutil.which", return_value="/usr/bin/git"):
            assert tools.check_tool("git") is True

    def test_not_found(self) -> None:
        with patch("ovms_release.tools.shutil.which", return_value=None):
            assert tools.check_tool("nonexistent") is False
