"""Tests for ops/notes.py."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from ovms_release.context import ReleaseContext
from ovms_release.ops import notes


@pytest.fixture
def ctx(tmp_path: Path) -> ReleaseContext:
    return ReleaseContext(version="2024.3", state_dir=tmp_path)


class TestGenerateNotes:
    def test_creates_file(self, ctx: ReleaseContext) -> None:
        with patch("ovms_release.tools.run_git") as mock_git:
            mock_git.return_value = subprocess.CompletedProcess([], 0, b"abc123 Fix bug\n", b"")
            result = notes.generate_notes(ctx)
            assert result.exists()
            content = result.read_text()
            assert "2024.3" in content
            assert "Fix bug" in content

    def test_handles_git_error(self, ctx: ReleaseContext) -> None:
        with patch(
            "ovms_release.tools.run_git",
            side_effect=subprocess.CalledProcessError(1, "git"),
        ):
            result = notes.generate_notes(ctx)
            assert result.exists()


class TestGenerateAudit:
    def test_creates_file(self, ctx: ReleaseContext) -> None:
        with patch("ovms_release.tools.run_gh") as mock_gh:
            mock_gh.return_value = subprocess.CompletedProcess([], 0, b"[]\n", b"")
            result = notes.generate_audit(ctx)
            assert result.exists()
            assert "Audit Report" in result.read_text()

    def test_handles_gh_error(self, ctx: ReleaseContext) -> None:
        with patch(
            "ovms_release.tools.run_gh",
            side_effect=subprocess.CalledProcessError(1, "gh"),
        ):
            result = notes.generate_audit(ctx)
            assert result.exists()
