"""Check container image labels for compliance.

Ports: check-image-labels.sh
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from ovms_release import tools

if TYPE_CHECKING:
    from ovms_release.context import ReleaseContext

REQUIRED_LABELS = [
    "com.redhat.component",
    "name",
    "version",
    "release",
    "summary",
    "description",
]


def check_image_labels(ctx: ReleaseContext, image_url: str) -> dict[str, str | None]:
    """Check image labels via skopeo. Returns label->value mapping (None if missing)."""
    try:
        out = tools.run_cmd(
            "skopeo",
            "inspect",
            f"docker://{image_url}",
            capture=True,
        )
        data = json.loads(out.stdout)
        labels = data.get("Labels", {})
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return {label: None for label in REQUIRED_LABELS}

    results: dict[str, str | None] = {}
    for label in REQUIRED_LABELS:
        results[label] = labels.get(label)
    return results


def validate_labels(ctx: ReleaseContext, image_url: str) -> list[str]:
    """Validate image has all required labels. Returns list of missing labels."""
    labels = check_image_labels(ctx, image_url)
    return [k for k, v in labels.items() if v is None]
