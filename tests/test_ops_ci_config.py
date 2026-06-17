"""Tests for ops/ci_config.py — mocks tools.* calls."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from ovms_release.context import ReleaseContext
from ovms_release.ops import ci_config


@pytest.fixture
def ctx() -> ReleaseContext:
    return ReleaseContext(version="2024.3")


class TestGetCiConfig:
    def test_produces_valid_config(self) -> None:
        config = ci_config.get_ci_config("2024", "3")
        assert config["org"] == "opendatahub-io"
        assert config["branch"] == "2024.3-release"
        assert "variants" in config
        assert "tests" in config


class TestValidateYaml:
    def test_valid(self) -> None:
        assert ci_config.validate_yaml("key: value\n") is True

    def test_invalid(self) -> None:
        assert ci_config.validate_yaml("key: [invalid\n") is False


class TestValidateBranchRefs:
    def test_correct_refs(self) -> None:
        config = {"branch": "2024.3-release"}
        assert ci_config.validate_branch_refs(config, "2024", "3") == []

    def test_wrong_refs(self) -> None:
        config = {"branch": "wrong-branch"}
        errors = ci_config.validate_branch_refs(config, "2024", "3")
        assert len(errors) == 1


class TestGenerateCiConfig:
    def test_returns_yaml(self, ctx: ReleaseContext) -> None:
        content = ci_config.generate_ci_config(ctx)
        assert "opendatahub-io" in content
        assert "2024.3-release" in content

    def test_writes_to_file(self, ctx: ReleaseContext, tmp_path: Path) -> None:
        output = tmp_path / "ci.yaml"
        ci_config.generate_ci_config(ctx, output=output)
        assert output.exists()
        assert "opendatahub-io" in output.read_text()


class TestUpdateCiConfig:
    def test_calls_make_update(self, ctx: ReleaseContext) -> None:
        with patch("ovms_release.tools.run_cmd") as mock_cmd:
            mock_cmd.return_value = subprocess.CompletedProcess([], 0, None, None)
            ci_config.update_ci_config(ctx)
            mock_cmd.assert_called_once_with("make", "update")
