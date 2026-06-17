"""Tests for ops/pypi.py."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

import pytest

from ovms_release.context import ReleaseContext
from ovms_release.ops import pypi


@pytest.fixture
def ctx() -> ReleaseContext:
    return ReleaseContext(version="2024.3")


class TestCheckPypiVersions:
    def test_success(self, ctx: ReleaseContext) -> None:
        response = json.dumps({"info": {"version": "2024.3.0"}}).encode()
        with patch("ovms_release.tools.run_cmd") as mock_cmd:
            mock_cmd.return_value = subprocess.CompletedProcess([], 0, response, b"")
            result = pypi.check_pypi_versions(ctx)
            assert all(v == "2024.3.0" for v in result.values())
            assert "openvino" in result

    def test_curl_fails(self, ctx: ReleaseContext) -> None:
        with patch(
            "ovms_release.tools.run_cmd",
            side_effect=subprocess.CalledProcessError(1, "curl"),
        ):
            result = pypi.check_pypi_versions(ctx)
            assert all(v == "error" for v in result.values())
