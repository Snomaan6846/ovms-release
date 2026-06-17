"""Shared pytest fixtures for ovms-release tests."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def tmp_state_dir(tmp_path):
    """Create a temporary state directory."""
    state_dir = tmp_path / ".ovms-release" / "openvino_model_server" / "2026.2"
    state_dir.mkdir(parents=True)
    return state_dir


@pytest.fixture
def sample_state():
    """Return a minimal valid release state."""
    return {
        "schema_version": 1,
        "status": "in_progress",
        "started_at": "2026-06-01T10:00:00+00:00",
        "started_by": "testuser",
        "aborted_at": "",
        "abort_reason": "",
        "abort_prs_closed": False,
        "phases": {
            "preflight": {"status": "completed", "notes": ""},
            "mirror_branches": {"status": "completed", "notes": ""},
            "push_owners": {"status": "pending", "notes": ""},
            "arg_review": {"status": "pending", "notes": ""},
            "local_build": {"status": "pending", "notes": ""},
            "ci_config": {"status": "pending", "notes": ""},
            "apply_patches": {"status": "pending", "patches_updated": False, "notes": ""},
            "odh_image_check": {"status": "pending", "notes": ""},
            "e2e_validation_release": {"status": "pending", "skipped_reason": "", "cluster_url": "", "ovms_image": "", "test_summary": "", "notes": ""},
            "sync_stable": {"status": "pending", "notes": ""},
            "e2e_validation_stable": {"status": "pending", "skipped_reason": "", "cluster_url": "", "ovms_image": "", "test_summary": "", "notes": ""},
            "sync_rhoai": {"status": "pending", "notes": ""},
            "rhds_auto_sync": {"status": "pending", "notes": ""},
        },
        "narrative": "",
        "config": {
            "year": "2026",
            "minor": "2",
            "upstream_org": "openvinotoolkit",
            "midstream_org": "opendatahub-io",
            "downstream_org": "red-hat-data-services",
            "upstream_branch": "releases/2026/2",
            "ovms_midstream_branch": "2026.2-release",
            "helper_midstream_branch": "releases/2026/2",
            "rhoai_version": "2.19",
            "base_image": "",
            "release_base_image": "",
            "driver_version": "",
            "lto_cxx_flags": "",
            "lto_ld_flags": "",
            "opendatahub_tests_image": "quay.io/opendatahub/opendatahub-tests:latest",
            "opendatahub_tests_path": "",
            "e2e_s3_bucket": "ods-ci-s3",
            "e2e_s3_region": "us-east-1",
            "e2e_s3_endpoint": "https://s3.us-east-1.amazonaws.com/",
            "e2e_ci_s3_endpoint": "https://s3.us-east-2.amazonaws.com/",
            "fork_remote": "origin",
            "midstream_remote": "midstream",
            "downstream_remote": "downstream",
            "jira_enabled": True,
            "jira_project": "RHOAIENG",
            "jira_component": "OVMS",
            "jira_server": "https://redhat.atlassian.net",
            "jira_ticket_url": "",
            "notification_webhook": "",
            "notification_events": ["phase_complete", "phase_failed", "build_ready", "e2e_result", "release_complete"],
        },
        "pr_urls": {
            "ci_config": "",
            "patches": "",
            "stable": "",
            "rhoai": "",
        },
    }


@pytest.fixture
def state_file(tmp_state_dir, sample_state):
    """Create a state file and return its path."""
    state_path = tmp_state_dir / "release-state.yaml"
    with open(state_path, "w") as f:
        yaml.dump(sample_state, f, default_flow_style=False, sort_keys=False)
    return state_path


@pytest.fixture
def monkeypatch_state_dir(monkeypatch, tmp_path):
    """Override HOME so state module uses tmp_path."""
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path
