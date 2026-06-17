#!/usr/bin/env python3
"""generate-ci-config.py — Phase 4: Generate openshift/release CI config.

Produces the YAML needed for openshift/release prow config and validates it.
Usage: generate-ci-config.py <VERSION> [--output <path>] [--validate-only]
"""

import argparse
import subprocess
import sys
import yaml
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Generate CI config for openshift/release")
    parser.add_argument("version", help="Release version (e.g., 2026.2)")
    parser.add_argument("--output", "-o", help="Output path (default: stdout)", default=None)
    parser.add_argument("--validate-only", action="store_true", help="Only validate existing config")
    parser.add_argument("--template", "-t", help="Template file path")
    return parser.parse_args()


def get_ci_config(year: str, minor: str) -> dict:
    """Generate the CI configuration for openshift/release."""
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
                        "from": f"ubi9/ubi-minimal",
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
    """Validate YAML syntax."""
    try:
        yaml.safe_load(content)
        return True
    except yaml.YAMLError as e:
        print(f"YAML validation failed: {e}", file=sys.stderr)
        return False


def validate_branch_refs(config: dict, year: str, minor: str) -> list[str]:
    """Check that branch references are consistent."""
    errors = []
    expected_branch = f"{year}.{minor}-release"
    if config.get("branch") != expected_branch:
        errors.append(f"Branch mismatch: expected '{expected_branch}', got '{config.get('branch')}'")
    return errors


def main():
    args = parse_args()
    parts = args.version.split(".")
    if len(parts) != 2:
        print(f"ERROR: Invalid version format: {args.version}", file=sys.stderr)
        sys.exit(1)
    year, minor = parts

    config = get_ci_config(year, minor)
    content = yaml.dump(config, default_flow_style=False, sort_keys=False)

    # Validate
    if not validate_yaml(content):
        sys.exit(1)

    ref_errors = validate_branch_refs(config, year, minor)
    if ref_errors:
        for err in ref_errors:
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)

    if args.validate_only:
        print("Validation passed.")
        sys.exit(0)

    # Output
    if args.output:
        Path(args.output).write_text(content)
        print(f"Config written to {args.output}")
    else:
        print(content)


if __name__ == "__main__":
    main()
