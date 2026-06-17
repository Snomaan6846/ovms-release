"""Tests for state management."""

import yaml
from pathlib import Path

from ovms_release.state import load_state, save_state, init_state, _migrate


def test_load_state(state_file):
    """State loads correctly from YAML."""
    state = load_state(state_file=state_file)
    assert state is not None
    assert state["status"] == "in_progress"
    assert state["config"]["year"] == "2026"
    assert state["config"]["minor"] == "2"


def test_load_state_missing():
    """Returns None for nonexistent file."""
    state = load_state(state_file=Path("/nonexistent/file.yaml"))
    assert state is None


def test_save_state(tmp_state_dir, sample_state):
    """State saves atomically."""
    path = tmp_state_dir / "release-state.yaml"
    result = save_state(sample_state, state_file=path)
    assert result == path
    assert path.exists()

    loaded = yaml.safe_load(path.read_text())
    assert loaded["status"] == "in_progress"
    assert loaded["schema_version"] == 1


def test_save_state_no_tmp_leftover(tmp_state_dir, sample_state):
    """Temp file is cleaned up after atomic write."""
    path = tmp_state_dir / "release-state.yaml"
    save_state(sample_state, state_file=path)
    tmp_file = path.with_suffix(".yaml.tmp")
    assert not tmp_file.exists()


def test_init_state():
    """New state has all required fields."""
    state = init_state("2026.2", started_by="testuser")
    assert state["schema_version"] == 1
    assert state["status"] == "in_progress"
    assert state["started_by"] == "testuser"
    assert state["config"]["year"] == "2026"
    assert state["config"]["minor"] == "2"
    assert state["config"]["upstream_branch"] == "releases/2026/2"
    assert state["config"]["ovms_midstream_branch"] == "2026.2-release"
    assert state["config"]["jira_project"] == "RHOAIENG"
    assert state["config"]["e2e_s3_bucket"] == "ods-ci-s3"
    assert "preflight" in state["phases"]
    assert "sync_rhoai" in state["phases"]


def test_migrate_v0_to_v1():
    """Migration adds missing fields."""
    old_state = {
        "status": "in_progress",
        "config": {"year": "2025", "minor": "1"},
    }
    migrated = _migrate(old_state)
    assert migrated["schema_version"] == 1
    assert migrated["aborted_at"] == ""
    assert migrated["config"]["jira_enabled"] is True
    assert migrated["config"]["jira_project"] == "RHOAIENG"
    assert migrated["config"]["e2e_s3_bucket"] == "ods-ci-s3"


def test_save_and_reload(tmp_state_dir):
    """Save then load produces identical state."""
    state = init_state("2026.3", started_by="user2")
    path = tmp_state_dir / "release-state.yaml"
    save_state(state, state_file=path)
    loaded = load_state(state_file=path)
    assert loaded["started_by"] == "user2"
    assert loaded["config"]["minor"] == "3"
