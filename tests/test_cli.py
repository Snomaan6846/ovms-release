"""Tests for CLI entry points — now tests ops/ module integration."""

from __future__ import annotations

from unittest.mock import patch

import yaml
from typer.testing import CliRunner

from ovms_release.cli import (
    diff_app,
    e2e_app,
    hotfix_app,
    patch_app,
    rebuild_app,
    release_app,
)

runner = CliRunner()


# --- Status / Resume / List / Abort (stateful commands) ---


def test_status_no_state(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(release_app, ["status"])
    assert result.exit_code == 0
    assert "No active release" in result.output


def test_status_with_state(monkeypatch, tmp_path, sample_state):
    import ovms_release.state as state_mod

    state_dir = tmp_path / "openvino_model_server" / "2026.2"
    state_dir.mkdir(parents=True)
    state_path = state_dir / "release-state.yaml"
    with open(state_path, "w") as f:
        yaml.dump(sample_state, f, default_flow_style=False, sort_keys=False)
    monkeypatch.setattr(state_mod, "DEFAULT_STATE_DIR", tmp_path / "openvino_model_server")
    result = runner.invoke(release_app, ["status"])
    assert result.exit_code == 0
    assert "2026.2" in result.output


def test_resume_no_state(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(release_app, ["resume"])
    assert result.exit_code == 1


def test_resume_with_state(monkeypatch, tmp_path, sample_state):
    import ovms_release.state as state_mod

    state_dir = tmp_path / "openvino_model_server" / "2026.2"
    state_dir.mkdir(parents=True)
    state_path = state_dir / "release-state.yaml"
    with open(state_path, "w") as f:
        yaml.dump(sample_state, f, default_flow_style=False, sort_keys=False)
    monkeypatch.setattr(state_mod, "DEFAULT_STATE_DIR", tmp_path / "openvino_model_server")
    result = runner.invoke(release_app, ["resume"])
    assert result.exit_code == 0
    assert "Resuming" in result.output


def test_list_no_releases(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(release_app, ["list"])
    assert result.exit_code == 0
    assert "No releases found" in result.output


def test_list_with_releases(monkeypatch, tmp_path, sample_state):
    import ovms_release.cli as cli_mod
    import ovms_release.state as state_mod

    state_dir = tmp_path / "openvino_model_server" / "2026.2"
    state_dir.mkdir(parents=True)
    state_path = state_dir / "release-state.yaml"
    with open(state_path, "w") as f:
        yaml.dump(sample_state, f, default_flow_style=False, sort_keys=False)
    monkeypatch.setattr(state_mod, "DEFAULT_STATE_DIR", tmp_path / "openvino_model_server")
    monkeypatch.setattr(cli_mod, "DEFAULT_STATE_DIR", tmp_path / "openvino_model_server")
    result = runner.invoke(release_app, ["list"])
    assert result.exit_code == 0
    assert "2026.2" in result.output


def test_abort_no_state(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    result = runner.invoke(release_app, ["abort", "--reason", "test"])
    assert result.exit_code == 1


def test_abort_with_state(monkeypatch, tmp_path, sample_state):
    import ovms_release.state as state_mod

    state_dir = tmp_path / "openvino_model_server" / "2026.2"
    state_dir.mkdir(parents=True)
    state_path = state_dir / "release-state.yaml"
    with open(state_path, "w") as f:
        yaml.dump(sample_state, f, default_flow_style=False, sort_keys=False)
    monkeypatch.setattr(state_mod, "DEFAULT_STATE_DIR", tmp_path / "openvino_model_server")
    result = runner.invoke(release_app, ["abort", "--reason", "testing abort"])
    assert result.exit_code == 0
    assert "aborted" in result.output


# --- Commands that call ops modules ---


def test_preflight_no_version():
    with patch("ovms_release.ops.preflight.detect_upstream_releases", return_value=["2024.4"]):
        result = runner.invoke(release_app, ["preflight"])
        assert result.exit_code == 0
        assert "2024.4" in result.output


def test_preflight_with_version():
    with patch("ovms_release.ops.preflight.run_preflight") as mock_pf:
        result = runner.invoke(release_app, ["preflight", "2024.3"])
        assert result.exit_code == 0
        mock_pf.assert_called_once()


def test_mirror_command():
    with patch("ovms_release.ops.mirror.mirror_branches") as mock_mirror:
        mock_mirror.return_value = {"model_server": "created"}
        result = runner.invoke(release_app, ["mirror", "2024.3"])
        assert result.exit_code == 0
        assert "model_server" in result.output


def test_owners_command():
    with patch("ovms_release.ops.owners.push_owners") as mock_owners:
        mock_owners.return_value = "https://github.com/org/repo/pull/1"
        result = runner.invoke(release_app, ["owners", "2024.3"])
        assert result.exit_code == 0
        assert "PR created" in result.output


def test_diff_args_command():
    from ovms_release.ops.diff_args import ArgDiff

    with patch("ovms_release.ops.diff_args.diff_args") as mock_diff:
        mock_diff.return_value = ArgDiff(changed={"OV_VERSION": ("1.0", "2.0")})
        result = runner.invoke(release_app, ["diff-args", "2024.3"])
        assert result.exit_code == 0
        assert "CHANGED" in result.output


def test_ci_config_command():
    result = runner.invoke(release_app, ["ci-config", "2024.3"])
    assert result.exit_code == 0
    assert "opendatahub-io" in result.output


def test_patch_command():
    with patch("ovms_release.ops.patches.apply_patches") as mock_patch:
        mock_patch.return_value = "https://github.com/org/repo/pull/5"
        result = runner.invoke(release_app, ["patch", "2024.3"])
        assert result.exit_code == 0
        assert "PR created" in result.output


def test_sync_stable_command():
    from ovms_release.context import TreeTransplantResult

    with patch("ovms_release.ops.sync_stable.tree_transplant") as mock_sync:
        mock_sync.return_value = TreeTransplantResult(success=True, pr_url="url")
        result = runner.invoke(release_app, ["sync-stable", "2024.3"])
        assert result.exit_code == 0
        assert "PR created" in result.output


def test_sync_rhoai_command():
    with patch("ovms_release.ops.sync_rhoai.sync_to_rhoai") as mock_sync:
        mock_sync.return_value = "url"
        result = runner.invoke(release_app, ["sync-rhoai", "2024.3", "--rhoai-version", "2.15"])
        assert result.exit_code == 0


def test_notes_command(tmp_path):
    from pathlib import Path

    with patch("ovms_release.ops.notes.generate_notes") as mock_notes:
        mock_notes.return_value = Path(tmp_path / "notes.md")
        (tmp_path / "notes.md").write_text("test")
        result = runner.invoke(release_app, ["notes", "2024.3"])
        assert result.exit_code == 0


def test_audit_command(tmp_path):
    from pathlib import Path

    with patch("ovms_release.ops.notes.generate_audit") as mock_audit:
        mock_audit.return_value = Path(tmp_path / "audit.md")
        (tmp_path / "audit.md").write_text("test")
        result = runner.invoke(release_app, ["audit", "2024.3"])
        assert result.exit_code == 0


# --- Utility apps ---


def test_diff_app():
    from ovms_release.ops.diff_args import ArgDiff

    with patch("ovms_release.ops.diff_args.diff_args") as mock_diff:
        mock_diff.return_value = ArgDiff(changed={"X": ("a", "b")})
        result = runner.invoke(diff_app, ["2024.2", "2024.3"])
        assert result.exit_code == 0


def test_rebuild_app():
    with patch("ovms_release.ops.rebuild.cve_rebuild") as mock_rebuild:
        mock_rebuild.return_value = "url"
        result = runner.invoke(rebuild_app, ["--branch", "2024.3-release"])
        assert result.exit_code == 0
        assert "PR created" in result.output


def test_hotfix_app():
    with patch("ovms_release.ops.hotfix.cherry_pick") as mock_cp:
        mock_cp.return_value = "url"
        result = runner.invoke(hotfix_app, ["abc123", "2024.3-release"])
        assert result.exit_code == 0


def test_patch_app():
    with patch("ovms_release.ops.patches.diagnose_patches") as mock_diag:
        mock_diag.return_value = {}
        result = runner.invoke(patch_app, ["2024.3"])
        assert result.exit_code == 0
        assert "All patches apply cleanly" in result.output


def test_e2e_app():
    with patch("ovms_release.ops.e2e.run_e2e") as mock_e2e:
        result = runner.invoke(e2e_app, ["quay.io/test:latest"])
        assert result.exit_code == 0
        mock_e2e.assert_called_once()


def test_e2e_app_error():
    from ovms_release.ops.e2e import E2EError

    with patch("ovms_release.ops.e2e.run_e2e", side_effect=E2EError("no runtime")):
        result = runner.invoke(e2e_app, ["quay.io/test:latest"])
        assert result.exit_code == 1


# --- Additional CLI coverage ---


def test_preflight_no_new_releases():
    with patch("ovms_release.ops.preflight.detect_upstream_releases", return_value=[]):
        result = runner.invoke(release_app, ["preflight"])
        assert result.exit_code == 0
        assert "already mirrored" in result.output


def test_preflight_error():
    from ovms_release.ops.preflight import PreflightError

    with patch("ovms_release.ops.preflight.run_preflight", side_effect=PreflightError("bad")):
        result = runner.invoke(release_app, ["preflight", "2024.3"])
        assert result.exit_code == 1
        assert "ERROR" in result.output


def test_mirror_error():
    from ovms_release.ops.mirror import MirrorError

    with patch("ovms_release.ops.mirror.mirror_branches", side_effect=MirrorError("fail")):
        result = runner.invoke(release_app, ["mirror", "2024.3"])
        assert result.exit_code == 1


def test_owners_dry_run():
    with patch("ovms_release.ops.owners.push_owners", return_value=None):
        result = runner.invoke(release_app, ["owners", "2024.3", "--dry-run"])
        assert result.exit_code == 0
        assert "up to date" in result.output


def test_diff_args_no_changes():
    from ovms_release.ops.diff_args import ArgDiff

    with patch("ovms_release.ops.diff_args.diff_args") as mock_diff:
        mock_diff.return_value = ArgDiff()
        result = runner.invoke(release_app, ["diff-args", "2024.3"])
        assert result.exit_code == 0
        assert "No ARG changes" in result.output


def test_diff_args_error():
    from ovms_release.ops.diff_args import ArgDiffError

    with patch("ovms_release.ops.diff_args.diff_args", side_effect=ArgDiffError("miss")):
        result = runner.invoke(release_app, ["diff-args", "2024.3"])
        assert result.exit_code == 1


def test_diff_args_added_removed():
    from ovms_release.ops.diff_args import ArgDiff

    with patch("ovms_release.ops.diff_args.diff_args") as mock_diff:
        mock_diff.return_value = ArgDiff(added={"A": "1"}, removed={"B": "2"})
        result = runner.invoke(release_app, ["diff-args", "2024.3"])
        assert result.exit_code == 0
        assert "NEW" in result.output
        assert "REMOVED" in result.output


def test_patch_error():
    from ovms_release.ops.patches import PatchError

    with patch("ovms_release.ops.patches.apply_patches", side_effect=PatchError("fail")):
        result = runner.invoke(release_app, ["patch", "2024.3"])
        assert result.exit_code == 1


def test_patch_dry_run():
    with patch("ovms_release.ops.patches.apply_patches", return_value=None):
        result = runner.invoke(release_app, ["patch", "2024.3", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output


def test_sync_stable_needs_confirm():
    from ovms_release.context import TreeTransplantResult

    with patch("ovms_release.ops.sync_stable.tree_transplant") as mock_sync:
        mock_sync.side_effect = [
            TreeTransplantResult(success=False, needs_confirm=True, untracked_files=["a.txt"]),
            TreeTransplantResult(success=True, pr_url="http://pr"),
        ]
        result = runner.invoke(release_app, ["sync-stable", "2024.3"], input="y\n")
        assert result.exit_code == 0
        assert "a.txt" in result.output


def test_sync_stable_success_no_pr():
    from ovms_release.context import TreeTransplantResult

    with patch("ovms_release.ops.sync_stable.tree_transplant") as mock_sync:
        mock_sync.return_value = TreeTransplantResult(success=True)
        result = runner.invoke(release_app, ["sync-stable", "2024.3"])
        assert result.exit_code == 0
        assert "Sync complete" in result.output


def test_sync_rhoai_empty_sync():
    from ovms_release.context import EmptySyncError

    with patch("ovms_release.ops.sync_rhoai.sync_to_rhoai", side_effect=EmptySyncError("empty")):
        result = runner.invoke(release_app, ["sync-rhoai", "2024.3", "--rhoai-version", "2.15"])
        assert result.exit_code == 1


def test_sync_rhoai_dry_run():
    with patch("ovms_release.ops.sync_rhoai.sync_to_rhoai", return_value=None):
        result = runner.invoke(release_app, ["sync-rhoai", "2024.3", "--rhoai-version", "2.15", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output


def test_rebuild_error():
    from ovms_release.ops.rebuild import RebuildError

    with patch("ovms_release.ops.rebuild.cve_rebuild", side_effect=RebuildError("oops")):
        result = runner.invoke(rebuild_app, ["--branch", "2024.3-release"])
        assert result.exit_code == 1


def test_rebuild_dry_run():
    with patch("ovms_release.ops.rebuild.cve_rebuild", return_value=None):
        result = runner.invoke(rebuild_app, ["--branch", "x", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output


def test_hotfix_error():
    from ovms_release.ops.hotfix import HotfixError

    with patch("ovms_release.ops.hotfix.cherry_pick", side_effect=HotfixError("oops")):
        result = runner.invoke(hotfix_app, ["abc", "branch"])
        assert result.exit_code == 1


def test_hotfix_already_present():
    with patch("ovms_release.ops.hotfix.cherry_pick", return_value=None):
        result = runner.invoke(hotfix_app, ["abc", "branch"])
        assert result.exit_code == 0
        assert "Already present" in result.output


def test_patch_app_failures():
    with patch("ovms_release.ops.patches.diagnose_patches") as mock_diag:
        mock_diag.return_value = {"01-fix.patch": "hunk failed"}
        result = runner.invoke(patch_app, ["2024.3"])
        assert result.exit_code == 0
        assert "01-fix.patch" in result.output


def test_status_with_narrative_and_prs(monkeypatch, tmp_path, sample_state):
    import ovms_release.state as state_mod

    sample_state["narrative"] = "Waiting for CI."
    sample_state["pr_urls"]["ci_config"] = "https://github.com/org/repo/pull/42"
    state_dir = tmp_path / "openvino_model_server" / "2026.2"
    state_dir.mkdir(parents=True)
    state_path = state_dir / "release-state.yaml"
    import yaml

    with open(state_path, "w") as f:
        yaml.dump(sample_state, f, default_flow_style=False, sort_keys=False)
    monkeypatch.setattr(state_mod, "DEFAULT_STATE_DIR", tmp_path / "openvino_model_server")
    result = runner.invoke(release_app, ["status"])
    assert result.exit_code == 0
    assert "Waiting for CI" in result.output
    assert "ci_config" in result.output


def test_abort_prompts_for_reason(monkeypatch, tmp_path, sample_state):
    import ovms_release.state as state_mod

    state_dir = tmp_path / "openvino_model_server" / "2026.2"
    state_dir.mkdir(parents=True)
    state_path = state_dir / "release-state.yaml"
    import yaml

    with open(state_path, "w") as f:
        yaml.dump(sample_state, f, default_flow_style=False, sort_keys=False)
    monkeypatch.setattr(state_mod, "DEFAULT_STATE_DIR", tmp_path / "openvino_model_server")
    result = runner.invoke(release_app, ["abort"], input="user reason\n")
    assert result.exit_code == 0
    assert "aborted" in result.output


def test_abort_shows_open_prs(monkeypatch, tmp_path, sample_state):
    import ovms_release.state as state_mod

    sample_state["pr_urls"]["patches"] = "https://github.com/org/repo/pull/11"
    state_dir = tmp_path / "openvino_model_server" / "2026.2"
    state_dir.mkdir(parents=True)
    state_path = state_dir / "release-state.yaml"
    import yaml

    with open(state_path, "w") as f:
        yaml.dump(sample_state, f, default_flow_style=False, sort_keys=False)
    monkeypatch.setattr(state_mod, "DEFAULT_STATE_DIR", tmp_path / "openvino_model_server")
    result = runner.invoke(release_app, ["abort", "--reason", "x"])
    assert result.exit_code == 0
    assert "Open PRs" in result.output
    assert "pull/11" in result.output


def test_list_with_empty_version_dir(monkeypatch, tmp_path):
    import ovms_release.cli as cli_mod
    import ovms_release.state as state_mod

    base = tmp_path / "openvino_model_server"
    (base / "2026.1").mkdir(parents=True)
    monkeypatch.setattr(state_mod, "DEFAULT_STATE_DIR", base)
    monkeypatch.setattr(cli_mod, "DEFAULT_STATE_DIR", base)
    result = runner.invoke(release_app, ["list"])
    assert result.exit_code == 0
    assert "Active releases" in result.output


def test_resume_all_phases_completed(monkeypatch, tmp_path, sample_state):
    import ovms_release.state as state_mod

    for phase in sample_state["phases"].values():
        phase["status"] = "completed"
    state_dir = tmp_path / "openvino_model_server" / "2026.2"
    state_dir.mkdir(parents=True)
    state_path = state_dir / "release-state.yaml"
    import yaml

    with open(state_path, "w") as f:
        yaml.dump(sample_state, f, default_flow_style=False, sort_keys=False)
    monkeypatch.setattr(state_mod, "DEFAULT_STATE_DIR", tmp_path / "openvino_model_server")
    result = runner.invoke(release_app, ["resume"])
    assert result.exit_code == 0
    assert "Resuming" in result.output
