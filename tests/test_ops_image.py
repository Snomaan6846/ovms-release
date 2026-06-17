"""Tests for ops/image.py."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

import pytest

from ovms_release.context import ReleaseContext
from ovms_release.ops import image


@pytest.fixture
def ctx() -> ReleaseContext:
    return ReleaseContext(version="2024.3")


class TestCheckImageLabels:
    def test_all_present(self, ctx: ReleaseContext) -> None:
        labels = {
            "com.redhat.component": "ovms",
            "name": "openvino-model-server",
            "version": "2024.3",
            "release": "1",
            "summary": "OpenVINO Model Server",
            "description": "Serving models with OpenVINO",
        }
        inspect_data = json.dumps({"Labels": labels}).encode()
        with patch("ovms_release.tools.run_cmd") as mock_cmd:
            mock_cmd.return_value = subprocess.CompletedProcess([], 0, inspect_data, b"")
            result = image.check_image_labels(ctx, "quay.io/test/image:latest")
            assert all(v is not None for v in result.values())

    def test_missing_labels(self, ctx: ReleaseContext) -> None:
        inspect_data = json.dumps({"Labels": {"name": "test"}}).encode()
        with patch("ovms_release.tools.run_cmd") as mock_cmd:
            mock_cmd.return_value = subprocess.CompletedProcess([], 0, inspect_data, b"")
            result = image.check_image_labels(ctx, "quay.io/test/image:latest")
            assert result["com.redhat.component"] is None

    def test_skopeo_fails(self, ctx: ReleaseContext) -> None:
        with patch(
            "ovms_release.tools.run_cmd",
            side_effect=subprocess.CalledProcessError(1, "skopeo"),
        ):
            result = image.check_image_labels(ctx, "quay.io/test/image:latest")
            assert all(v is None for v in result.values())


class TestValidateLabels:
    def test_all_ok(self, ctx: ReleaseContext) -> None:
        labels = {label: "val" for label in image.REQUIRED_LABELS}
        inspect_data = json.dumps({"Labels": labels}).encode()
        with patch("ovms_release.tools.run_cmd") as mock_cmd:
            mock_cmd.return_value = subprocess.CompletedProcess([], 0, inspect_data, b"")
            assert image.validate_labels(ctx, "quay.io/test:latest") == []

    def test_missing(self, ctx: ReleaseContext) -> None:
        with patch(
            "ovms_release.tools.run_cmd",
            side_effect=subprocess.CalledProcessError(1, "skopeo"),
        ):
            missing = image.validate_labels(ctx, "quay.io/test:latest")
            assert len(missing) == len(image.REQUIRED_LABELS)
