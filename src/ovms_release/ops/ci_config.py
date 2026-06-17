"""Phase 4: Generate openshift/release CI config.

Ports: scripts/generate-ci-config.py
Produces YAML for openshift/release prow config and validates it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml

from ovms_release import tools

if TYPE_CHECKING:
    from pathlib import Path

    from ovms_release.context import ReleaseContext


class CIConfigError(Exception):
    """Raised when CI config generation or validation fails."""


def get_ci_config(year: str, minor: str) -> dict:
    """Generate the CI configuration dict for openshift/release."""
    branch = f"{year}.{minor}-release"
    return {
        "org": "opendatahub-io",
        "repo": "openvino_model_server",
        "branch": branch,
        "variants": {
            "v4.14": {
                "build_root_image": {
                    "name": "release",
                    "namespace": "openshift",
                    "tag": "golang-1.21",
                },
                "images": [
                    {
                        "dockerfile_path": "Dockerfile.redhat",
                        "from": "ubi9/ubi-minimal",
                        "to": "openvino-model-server",
                    }
                ],
                "promotion": {
                    "namespace": "ocp",
                    "name": f"{year}.{minor}",
                },
                "resources": {
                    "requests": {
                        "cpu": "8",
                        "memory": "16Gi",
                    }
                },
            }
        },
        "tests": [
            {
                "as": "e2e",
                "steps": {
                    "test": [
                        {
                            "as": "e2e-openvino",
                            "from": "openvino-model-server",
                            "commands": "echo 'E2E tests placeholder'",
                        }
                    ]
                },
            }
        ],
    }


def validate_yaml(content: str) -> bool:
    """Validate YAML syntax. Returns True if valid."""
    try:
        yaml.safe_load(content)
        return True
    except yaml.YAMLError:
        return False


def validate_branch_refs(config: dict, year: str, minor: str) -> list[str]:
    """Check that branch references are consistent."""
    errors: list[str] = []
    expected_branch = f"{year}.{minor}-release"
    if config.get("branch") != expected_branch:
        errors.append(f"Branch mismatch: expected '{expected_branch}', got '{config.get('branch')}'")
    return errors


def generate_ci_config(ctx: ReleaseContext, output: Path | None = None) -> str:
    """Generate CI config YAML. Optionally writes to output path.

    Returns the YAML content string.
    Raises CIConfigError on validation failure.
    """
    config = get_ci_config(ctx.year, ctx.minor)
    content = yaml.dump(config, default_flow_style=False, sort_keys=False)

    if not validate_yaml(content):
        raise CIConfigError("Generated YAML is invalid")

    ref_errors = validate_branch_refs(config, ctx.year, ctx.minor)
    if ref_errors:
        raise CIConfigError(f"Branch validation failed: {ref_errors}")

    if output:
        output.write_text(content)

    return content


def update_ci_config(ctx: ReleaseContext) -> None:
    """Generate config and run make update to apply it."""
    generate_ci_config(ctx)
    tools.run_cmd("make", "update")
