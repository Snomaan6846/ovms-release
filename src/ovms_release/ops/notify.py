"""Webhook notifications for release events.

Ports: notify.sh
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING

from ovms_release import tools

if TYPE_CHECKING:
    from ovms_release.context import ReleaseContext


def send_notification(
    ctx: ReleaseContext,
    event: str,
    message: str,
    *,
    webhook_url: str | None = None,
) -> bool:
    """Send webhook notification. Returns True on success, False if no webhook configured."""
    url = webhook_url or os.environ.get("NOTIFICATION_WEBHOOK", "")
    if not url:
        return False

    payload = json.dumps(
        {
            "event": event,
            "message": message,
            "version": ctx.version,
            "dry_run": ctx.dry_run,
        }
    )

    try:
        tools.run_cmd(
            "curl",
            "-sS",
            "-X",
            "POST",
            "-H",
            "Content-Type: application/json",
            "-d",
            payload,
            url,
            capture=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False
