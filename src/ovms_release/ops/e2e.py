"""E2E test execution via container runtime.

Ports: run-e2e-tests.sh
Uses capture=False for live streaming of long-running test output.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ovms_release import tools

if TYPE_CHECKING:
    from ovms_release.context import ReleaseContext


class E2EError(Exception):
    """Raised when E2E pre-checks or tests fail."""


def run_e2e(
    ctx: ReleaseContext,
    image: str,
    *,
    smoke_only: bool = False,
    test_filter: str = "",
    test_path: str = "tests/model_serving/model_runtime/openvino/",
) -> None:
    """Run E2E tests in container. Streams output live (capture=False).

    Raises E2EError if pre-checks fail or tests fail.
    """
    if tools.check_tool("podman"):
        runtime = "podman"
    elif tools.check_tool("docker"):
        runtime = "docker"
    else:
        raise E2EError("podman or docker required for E2E tests")

    if not tools.check_tool("oc"):
        raise E2EError("oc CLI required")

    for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        if not os.environ.get(var):
            raise E2EError(f"{var} not set")

    odt_image = os.environ.get("ODT_IMAGE", "quay.io/opendatahub/opendatahub-tests:latest")
    kubeconfig = os.environ.get("KUBECONFIG", os.path.expanduser("~/.kube/config"))
    s3_bucket = os.environ.get("E2E_S3_BUCKET", "ods-ci-s3")
    s3_region = os.environ.get("E2E_S3_REGION", "us-east-1")
    s3_endpoint = os.environ.get("E2E_S3_ENDPOINT", "https://s3.us-east-1.amazonaws.com/")
    ci_s3_endpoint = os.environ.get("E2E_CI_S3_ENDPOINT", "https://s3.us-east-2.amazonaws.com/")

    pytest_args = f"-v -s {test_path}"
    if smoke_only:
        pytest_args += " -k basic"
    if test_filter:
        pytest_args += f" -k {test_filter}"

    tools.run_cmd(
        runtime,
        "run",
        "--rm",
        "-e",
        f"AWS_ACCESS_KEY_ID={os.environ.get('AWS_ACCESS_KEY_ID', '')}",
        "-e",
        f"AWS_SECRET_ACCESS_KEY={os.environ.get('AWS_SECRET_ACCESS_KEY', '')}",
        "-e",
        "KUBECONFIG=/kube/config",
        "-v",
        f"{kubeconfig}:/kube/config:ro",
        odt_image,
        "pytest",
        *pytest_args.split(),
        f"--models-s3-bucket-name={s3_bucket}",
        f"--models-s3-bucket-region={s3_region}",
        f"--models-s3-bucket-endpoint={s3_endpoint}",
        f"--ci-s3-bucket-endpoint={ci_s3_endpoint}",
        f"--ovms-runtime-image={image}",
    )
