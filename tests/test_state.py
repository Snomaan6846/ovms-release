"""Tests for state management."""

from pathlib import Path

import yaml

from ovms_release.state import _migrate, init_state, load_state, save_state


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
    assert loaded is not None
    assert loaded["started_by"] == "user2"
    assert loaded["config"]["minor"] == "3"


def test_load_state_by_version(monkeypatch, tmp_path, sample_state):
    """load_state with version= finds correct state file."""
    import ovms_release.state as state_mod

    state_dir = tmp_path / "2026.2"
    state_dir.mkdir(parents=True)
    state_path = state_dir / "release-state.yaml"
    with open(state_path, "w") as f:
        yaml.dump(sample_state, f, default_flow_style=False, sort_keys=False)
    monkeypatch.setattr(state_mod, "DEFAULT_STATE_DIR", tmp_path)
    state = load_state(version="2026.2")
    assert state is not None
    assert state["config"]["year"] == "2026"


def test_load_state_invalid_yaml(tmp_path):
    """load_state returns None for non-dict YAML content."""
    state_path = tmp_path / "bad-state.yaml"
    state_path.write_text("just a string\n")
    state = load_state(state_file=state_path)
    assert state is None


def test_save_state_by_version(monkeypatch, tmp_path, sample_state):
    """save_state with version= creates file in correct location."""
    import ovms_release.state as state_mod

    monkeypatch.setattr(state_mod, "DEFAULT_STATE_DIR", tmp_path)
    result = save_state(sample_state, version="2026.2")
    assert result == tmp_path / "2026.2" / "release-state.yaml"
    assert result.exists()
    loaded = yaml.safe_load(result.read_text())
    assert loaded["status"] == "in_progress"


def test_load_state_auto_detect_skips_dirs_without_state(monkeypatch, tmp_path, sample_state):
    """Auto-detection skips dirs without release-state.yaml."""
    import ovms_release.state as state_mod

    (tmp_path / "2026.1").mkdir()
    good_dir = tmp_path / "2026.2"
    good_dir.mkdir()
    state_path = good_dir / "release-state.yaml"
    with open(state_path, "w") as f:
        yaml.dump(sample_state, f, default_flow_style=False, sort_keys=False)
    monkeypatch.setattr(state_mod, "DEFAULT_STATE_DIR", tmp_path)
    state = load_state()
    assert state is not None
    assert state["config"]["minor"] == "2"


def test_load_state_auto_detect_empty_dir(monkeypatch, tmp_path):
    """Auto-detection returns None when no state files exist."""
    import ovms_release.state as state_mod

    (tmp_path / "2026.1").mkdir()
    (tmp_path / "2026.2").mkdir()
    monkeypatch.setattr(state_mod, "DEFAULT_STATE_DIR", tmp_path)
    state = load_state()
    assert state is None
