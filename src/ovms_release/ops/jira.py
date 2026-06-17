"""Jira integration for release tracking.

Ports: jira-integration.sh
Note: non-acli update-status remains manual with a log warning (documented REST gap).
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import TYPE_CHECKING

from ovms_release import tools

if TYPE_CHECKING:
    from ovms_release.context import ReleaseContext

logger = logging.getLogger(__name__)


class JiraError(Exception):
    """Raised when Jira operation fails."""


def transition_issue(ctx: ReleaseContext, issue_key: str, status: str) -> bool:
    """Transition a Jira issue to a new status. Returns True on success."""
    if tools.check_tool("acli"):
        try:
            tools.run_cmd(
                "acli",
                "jira",
                "transition",
                issue_key,
                status,
                capture=True,
            )
            return True
        except subprocess.CalledProcessError:
            logger.warning("acli transition failed for %s -> %s", issue_key, status)
            return False

    jira_token = os.environ.get("JIRA_API_TOKEN", "")
    jira_email = os.environ.get("JIRA_USER_EMAIL", "")
    if jira_token and jira_email:
        logger.warning(
            "REST API status transition not fully automated. Manually transition %s to '%s' in Jira.",
            issue_key,
            status,
        )
        return False

    logger.warning("No Jira backend configured; skipping transition for %s", issue_key)
    return False


def add_comment(ctx: ReleaseContext, issue_key: str, comment: str) -> bool:
    """Add a comment to a Jira issue. Returns True on success."""
    if tools.check_tool("acli"):
        try:
            tools.run_cmd(
                "acli",
                "jira",
                "addComment",
                issue_key,
                comment,
                capture=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    logger.warning("Cannot add comment without acli for %s", issue_key)
    return False


def create_release_issue(ctx: ReleaseContext, project: str = "RHOAIENG") -> str | None:
    """Create a release tracking issue. Returns issue key or None."""
    if not tools.check_tool("acli"):
        logger.warning("acli not available; cannot create Jira issue")
        return None

    try:
        out = tools.run_cmd(
            "acli",
            "jira",
            "createIssue",
            "--project",
            project,
            "--type",
            "Task",
            "--summary",
            f"OVMS {ctx.version} Release",
            "--description",
            f"Track OVMS {ctx.version} release process.",
            capture=True,
        )
        return out.stdout.decode().strip()
    except subprocess.CalledProcessError:
        return None
