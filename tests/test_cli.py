"""Tests for CLI entry points (smoke tests)."""

from typer.testing import CliRunner
from ovms_release.cli import release_app

runner = CliRunner()


def test_status_no_state(monkeypatch, tmp_path):
    """Status command handles no active release gracefully."""
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(release_app, ["status"])
    assert result.exit_code == 0
    assert "No active release" in result.output


def test_resume_no_state(monkeypatch, tmp_path):
    """Resume command handles no active release."""
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(release_app, ["resume"])
    assert result.exit_code == 1
    assert "No active release" in result.output


def test_list_no_releases(monkeypatch, tmp_path):
    """List command handles empty state dir."""
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(release_app, ["list"])
    assert result.exit_code == 0
    assert "No releases found" in result.output


def test_abort_no_state(monkeypatch, tmp_path):
    """Abort command handles no active release."""
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(release_app, ["abort", "--reason", "test"])
    assert result.exit_code == 1
    assert "No active release" in result.output
