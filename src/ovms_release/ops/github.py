"""GitHub PR status checking.

Ports: check-pr-status.sh (GAP 6 — wrong home was state.py)
"""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

from ovms_release import tools

if TYPE_CHECKING:
    from ovms_release.context import ReleaseContext


def check_pr_status(ctx: ReleaseContext, pr_url: str) -> dict[str, str]:
    """Check status of a PR. Returns dict with state, mergeable, checks info."""
    try:
        out = tools.run_gh(
            "pr",
            "view",
            pr_url,
            "--json",
            "state,mergeable,statusCheckRollup,title",
            capture=True,
        )
        data = json.loads(out.stdout)
        checks = data.get("statusCheckRollup", [])
        check_summary = "all_pass"
        for check in checks:
            if check.get("conclusion") not in ("SUCCESS", "success", "NEUTRAL", "neutral", None):
                check_summary = "has_failures"
                break

        return {
            "state": data.get("state", "UNKNOWN"),
            "mergeable": data.get("mergeable", "UNKNOWN"),
            "checks": check_summary,
            "title": data.get("title", ""),
        }
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return {"state": "ERROR", "mergeable": "UNKNOWN", "checks": "unknown", "title": ""}


def list_release_prs(ctx: ReleaseContext) -> list[dict[str, str]]:
    """List PRs related to the current release."""
    try:
        out = tools.run_gh(
            "pr",
            "list",
            "--repo",
            "opendatahub-io/openvino_model_server",
            "--state",
            "all",
            "--search",
            ctx.version,
            "--json",
            "number,title,state,url",
            capture=True,
        )
        result: list[dict[str, str]] = json.loads(out.stdout)
        return result
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return []
