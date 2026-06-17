"""State file read/write with schema migration logic."""

from pathlib import Path
from typing import Any

import yaml

CURRENT_SCHEMA = 1
DEFAULT_STATE_DIR = Path.home() / ".ovms-release" / "openvino_model_server"


def _get_state_path(version: str | None = None, state_file: Path | None = None) -> Path | None:
    if state_file:
        return state_file
    if version:
        return DEFAULT_STATE_DIR / version / "release-state.yaml"
    # Find most recent state file
    if DEFAULT_STATE_DIR.exists():
        candidates = sorted(DEFAULT_STATE_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        for d in candidates:
            sf = d / "release-state.yaml"
            if sf.exists():
                return sf
    return None


def load_state(state_file: Path | None = None, version: str | None = None) -> dict[str, Any] | None:
    path = _get_state_path(version=version, state_file=state_file)
    if path is None or not path.exists():
        return None
    with open(path) as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        return None
    state: dict[str, Any] = _migrate(raw)
    return state


def save_state(state: dict[str, Any], version: str | None = None, state_file: Path | None = None) -> Path:
    if state_file:
        path = state_file
    elif version:
        path = DEFAULT_STATE_DIR / version / "release-state.yaml"
    else:
        v = f"{state.get('config', {}).get('year', 'unknown')}.{state.get('config', {}).get('minor', 'unknown')}"
        path = DEFAULT_STATE_DIR / v / "release-state.yaml"

    path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: write to temp then rename
    tmp = path.with_suffix(".yaml.tmp")
    state["schema_version"] = CURRENT_SCHEMA
    with open(tmp, "w") as f:
        yaml.dump(state, f, default_flow_style=False, sort_keys=False)
    tmp.rename(path)
    return path


def _migrate(state: dict[str, Any]) -> dict[str, Any]:
    schema = state.get("schema_version", 0)
    if schema < 1:
        state = _migrate_v0_to_v1(state)
    return state


def _migrate_v0_to_v1(state: dict[str, Any]) -> dict[str, Any]:
    state.setdefault("schema_version", 1)
    state.setdefault("aborted_at", "")
    state.setdefault("abort_reason", "")
    state.setdefault("abort_prs_closed", False)
    config = state.setdefault("config", {})
    config.setdefault("jira_enabled", True)
    config.setdefault("jira_project", "RHOAIENG")
    config.setdefault("jira_component", "OVMS")
    config.setdefault("jira_server", "https://redhat.atlassian.net")
    config.setdefault("jira_ticket_url", "")
    config.setdefault("notification_webhook", "")
    config.setdefault(
        "notification_events", ["phase_complete", "phase_failed", "build_ready", "e2e_result", "release_complete"]
    )
    config.setdefault("e2e_s3_bucket", "ods-ci-s3")
    config.setdefault("e2e_s3_region", "us-east-1")
    config.setdefault("e2e_s3_endpoint", "https://s3.us-east-1.amazonaws.com/")
    config.setdefault("e2e_ci_s3_endpoint", "https://s3.us-east-2.amazonaws.com/")
    return state


def init_state(version: str, started_by: str = "") -> dict[str, Any]:
    """Create a new release state with default values."""
    from datetime import datetime, timezone

    year, minor = parse_version_tuple(version)
    return {
        "schema_version": CURRENT_SCHEMA,
        "status": "in_progress",
        "started_at": datetime.now(tz=timezone.utc).isoformat(),
        "started_by": started_by,
        "aborted_at": "",
        "abort_reason": "",
        "abort_prs_closed": False,
        "phases": {
            "preflight": {"status": "pending", "notes": ""},
            "mirror_branches": {"status": "pending", "notes": ""},
            "push_owners": {"status": "pending", "notes": ""},
            "arg_review": {"status": "pending", "notes": ""},
            "local_build": {"status": "pending", "notes": ""},
            "ci_config": {"status": "pending", "notes": ""},
            "apply_patches": {"status": "pending", "patches_updated": False, "notes": ""},
            "odh_image_check": {"status": "pending", "notes": ""},
            "e2e_validation_release": {
                "status": "pending",
                "skipped_reason": "",
                "cluster_url": "",
                "ovms_image": "",
                "test_summary": "",
                "notes": "",
            },
            "sync_stable": {"status": "pending", "notes": ""},
            "e2e_validation_stable": {
                "status": "pending",
                "skipped_reason": "",
                "cluster_url": "",
                "ovms_image": "",
                "test_summary": "",
                "notes": "",
            },
            "sync_rhoai": {"status": "pending", "notes": ""},
            "rhds_auto_sync": {"status": "pending", "notes": ""},
        },
        "narrative": "",
        "config": {
            "year": year,
            "minor": minor,
            "upstream_org": "openvinotoolkit",
            "midstream_org": "opendatahub-io",
            "downstream_org": "red-hat-data-services",
            "upstream_branch": f"releases/{year}/{minor}",
            "ovms_midstream_branch": f"{year}.{minor}-release",
            "helper_midstream_branch": f"releases/{year}/{minor}",
            "rhoai_version": "",
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


def parse_version_tuple(version: str) -> tuple[str, str]:
    """Parse '2026.2' into ('2026', '2')."""
    parts = version.split(".")
    if len(parts) != 2:
        raise ValueError(f"Invalid version format: {version} (expected YEAR.MINOR)")
    return parts[0], parts[1]
