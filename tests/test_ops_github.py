"""Tests for ops/github.py."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

import pytest

from ovms_release.context import ReleaseContext
from ovms_release.ops import github


@pytest.fixture
def ctx() -> ReleaseContext:
    return ReleaseContext(version="2024.3")


class TestCheckPrStatus:
    def test_success(self, ctx: ReleaseContext) -> None:
        pr_data = json.dumps(
            {
                "state": "OPEN",
                "mergeable": "MERGEABLE",
                "statusCheckRollup": [{"conclusion": "SUCCESS"}],
                "title": "Test PR",
            }
        ).encode()
        with patch("ovms_release.tools.run_gh") as mock_gh:
            mock_gh.return_value = subprocess.CompletedProcess([], 0, pr_data, b"")
            result = github.check_pr_status(ctx, "https://github.com/org/repo/pull/1")
            assert result["state"] == "OPEN"
            assert result["checks"] == "all_pass"

    def test_failing_checks(self, ctx: ReleaseContext) -> None:
        pr_data = json.dumps(
            {
                "state": "OPEN",
                "mergeable": "MERGEABLE",
                "statusCheckRollup": [{"conclusion": "FAILURE"}],
                "title": "PR",
            }
        ).encode()
        with patch("ovms_release.tools.run_gh") as mock_gh:
            mock_gh.return_value = subprocess.CompletedProcess([], 0, pr_data, b"")
            result = github.check_pr_status(ctx, "url")
            assert result["checks"] == "has_failures"

    def test_gh_fails(self, ctx: ReleaseContext) -> None:
        with patch(
            "ovms_release.tools.run_gh",
            side_effect=subprocess.CalledProcessError(1, "gh"),
        ):
            result = github.check_pr_status(ctx, "url")
            assert result["state"] == "ERROR"


class TestListReleasePrs:
    def test_success(self, ctx: ReleaseContext) -> None:
        data = json.dumps([{"number": 1, "title": "Test", "state": "OPEN", "url": "url"}]).encode()
        with patch("ovms_release.tools.run_gh") as mock_gh:
            mock_gh.return_value = subprocess.CompletedProcess([], 0, data, b"")
            result = github.list_release_prs(ctx)
            assert len(result) == 1

    def test_gh_fails(self, ctx: ReleaseContext) -> None:
        with patch(
            "ovms_release.tools.run_gh",
            side_effect=subprocess.CalledProcessError(1, "gh"),
        ):
            assert github.list_release_prs(ctx) == []
