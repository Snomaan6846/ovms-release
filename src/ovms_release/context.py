"""Shared types for OVMS release automation.

This module defines ReleaseContext (the single configuration object threaded
through all ops/ functions), TreeTransplantResult, and EmptySyncError.

Import direction rule:
  context.py may import from state.py (for DEFAULT_STATE_DIR, parse_version_tuple).
  state.py must NEVER import from context.py (one-way dependency).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING

from ovms_release.state import DEFAULT_STATE_DIR, parse_version_tuple

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class ReleaseContext:
    """Single configuration object passed to all ops/ module functions."""

    version: str
    dry_run: bool = False
    fork_remote: str = "origin"
    midstream_remote: str = "midstream"
    downstream_remote: str = "downstream"
    rhoai_version: str = ""
    state_dir: Path = field(default_factory=lambda: DEFAULT_STATE_DIR)

    @cached_property
    def year(self) -> str:
        return parse_version_tuple(self.version)[0]

    @cached_property
    def minor(self) -> str:
        return parse_version_tuple(self.version)[1]


@dataclass
class TreeTransplantResult:
    """Result of a tree transplant operation (sync to stable)."""

    success: bool
    needs_confirm: bool = False
    untracked_files: list[str] = field(default_factory=list)
    pr_url: str = ""


class EmptySyncError(Exception):
    """Raised when sync-to-rhoai produces no changes."""
