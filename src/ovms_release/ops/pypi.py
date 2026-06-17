"""Check PyPI package versions for Python dependencies.

Ports: scripts/check-pypi-versions.py
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from ovms_release import tools

if TYPE_CHECKING:
    from ovms_release.context import ReleaseContext

PACKAGES_TO_CHECK = [
    "openvino",
    "openvino-tokenizers",
    "openvino-genai",
    "optimum-intel",
]


def check_pypi_versions(ctx: ReleaseContext) -> dict[str, str]:
    """Query PyPI for latest versions of key packages. Returns package->version."""
    results: dict[str, str] = {}
    for package in PACKAGES_TO_CHECK:
        try:
            out = tools.run_cmd(
                "curl",
                "-sL",
                f"https://pypi.org/pypi/{package}/json",
                capture=True,
            )
            data = json.loads(out.stdout)
            results[package] = data.get("info", {}).get("version", "unknown")
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            results[package] = "error"
    return results
