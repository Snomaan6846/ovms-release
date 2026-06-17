"""Tests for repo-specific branch naming conventions."""

from ovms_release.config import (
    MIDSTREAM_REPOS,
    UPSTREAM_REPOS,
    get_branch_name,
    get_downstream_branch,
    get_stable_branch,
    get_upstream_branch,
)


def test_ovms_midstream_uses_year_minor_release():
    """openvino_model_server uses YEAR.MINOR-release format."""
    assert get_branch_name("openvino_model_server", "2026", "2") == "2026.2-release"
    assert get_branch_name("openvino_model_server", "2025", "4") == "2025.4-release"


def test_helper_repos_use_releases_path():
    """Non-OVMS repos use releases/YEAR/MINOR format."""
    for repo in ["openvino", "openvino.genai", "openvino_tokenizers"]:
        assert get_branch_name(repo, "2026", "2") == "releases/2026/2"


def test_upstream_branch_always_uses_releases_path():
    """All upstream repos (including model_server) use releases/YEAR/MINOR."""
    assert get_upstream_branch("2026", "2") == "releases/2026/2"


def test_stable_branch():
    assert get_stable_branch() == "stable"


def test_downstream_branch():
    assert get_downstream_branch("2.19") == "rhoai-2.19"
    assert get_downstream_branch("3.5") == "rhoai-3.5"


def test_upstream_repos_has_4_entries():
    assert len(UPSTREAM_REPOS) == 4


def test_midstream_repos_has_4_entries():
    assert len(MIDSTREAM_REPOS) == 4


def test_repo_name_mismatch_documented():
    """Upstream uses 'model_server', midstream uses 'openvino_model_server'."""
    upstream_names = [r[1] for r in UPSTREAM_REPOS]
    midstream_names = [r[1] for r in MIDSTREAM_REPOS]
    assert "model_server" in upstream_names
    assert "openvino_model_server" in midstream_names
    assert "model_server" not in midstream_names
