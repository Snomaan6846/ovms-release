"""Tests for config module."""

import pytest

from ovms_release.config import (
    get_branch_name,
    get_downstream_branch,
    get_stable_branch,
    get_upstream_branch,
    parse_version,
)


def test_parse_version():
    assert parse_version("2026.2") == ("2026", "2")
    assert parse_version("2025.10") == ("2025", "10")


def test_parse_version_invalid():
    with pytest.raises(ValueError):
        parse_version("2026")
    with pytest.raises(ValueError):
        parse_version("2026.2.1")


def test_get_branch_name_ovms():
    """openvino_model_server uses YEAR.MINOR-release."""
    assert get_branch_name("openvino_model_server", "2026", "2") == "2026.2-release"


def test_get_branch_name_helper():
    """Helper repos use releases/YEAR/MINOR."""
    assert get_branch_name("openvino", "2026", "2") == "releases/2026/2"
    assert get_branch_name("openvino.genai", "2026", "2") == "releases/2026/2"
    assert get_branch_name("openvino_tokenizers", "2026", "2") == "releases/2026/2"


def test_get_upstream_branch():
    assert get_upstream_branch("2026", "2") == "releases/2026/2"


def test_get_stable_branch():
    assert get_stable_branch() == "stable"


def test_get_downstream_branch():
    assert get_downstream_branch("2.19") == "rhoai-2.19"
