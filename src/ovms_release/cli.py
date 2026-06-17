"""Typer-based CLI with multiple entry points for OVMS release automation."""

import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer

from ovms_release.config import get_branch_name, parse_version
from ovms_release.state import load_state, save_state

SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"

# --- Main release app ---

release_app = typer.Typer(
    name="ovms-release",
    help="OVMS release automation CLI with pre-flight intelligence and stateful tracking.",
    no_args_is_help=True,
)


def _run_script(name: str, args: list[str] | None = None, dry_run: bool = False) -> int:
    script = SCRIPTS_DIR / name
    if not script.exists():
        typer.echo(f"ERROR: Script not found: {script}", err=True)
        raise typer.Exit(1)
    env_vars = {}
    if dry_run:
        env_vars["DRY_RUN"] = "1"
    cmd = ["bash", str(script)] + (args or [])
    result = subprocess.run(cmd, env={**subprocess.os.environ, **env_vars})
    return result.returncode


@release_app.command()
def preflight(
    version: Optional[str] = typer.Argument(None, help="Release version (e.g., 2026.2)"),
):
    """Phase 0: Gather intelligence and produce Release Brief."""
    args = [version] if version else []
    rc = _run_script("preflight.sh", args)
    raise typer.Exit(rc)


@release_app.command()
def mirror(version: str = typer.Argument(..., help="Release version")):
    """Phase 1: Create mirror branches in 4 ODH repos."""
    rc = _run_script("mirror-branches.sh", [version])
    raise typer.Exit(rc)


@release_app.command()
def owners(version: str = typer.Argument(..., help="Release version")):
    """Phase 2: Push OWNERS file via PR."""
    rc = _run_script("push-owners.sh", [version])
    raise typer.Exit(rc)


@release_app.command(name="diff-args")
def diff_args(version: str = typer.Argument(..., help="Release version")):
    """Phase 3: ARG diff report between releases."""
    rc = _run_script("diff-args.sh", [version])
    raise typer.Exit(rc)


@release_app.command(name="ci-config")
def ci_config(version: str = typer.Argument(..., help="Release version")):
    """Phase 4: Generate openshift/release CI config PR."""
    rc = _run_script("generate-ci-config.py", [version])
    raise typer.Exit(rc)


@release_app.command()
def patch(version: str = typer.Argument(..., help="Release version")):
    """Phase 5: Apply patches and create PR."""
    rc = _run_script("apply-patches.sh", [version])
    raise typer.Exit(rc)


@release_app.command(name="sync-stable")
def sync_stable(version: str = typer.Argument(..., help="Release version")):
    """Phase 6: Tree transplant merge to stable branch."""
    rc = _run_script("tree-transplant.sh", [version])
    raise typer.Exit(rc)


@release_app.command(name="sync-rhoai")
def sync_rhoai():
    """Phase 7: Sync stable to rhoai branch."""
    rc = _run_script("sync-to-rhoai.sh")
    raise typer.Exit(rc)


@release_app.command()
def status():
    """Show current release state (read-only)."""
    state = load_state()
    if state is None:
        typer.echo("No active release found.")
        raise typer.Exit(0)
    typer.echo(f"Release {state.get('config', {}).get('year', '?')}.{state.get('config', {}).get('minor', '?')}")
    typer.echo(f"Status: {state.get('status', 'unknown')}")
    if state.get("narrative"):
        typer.echo(f"\n{state['narrative'].strip()}")
    pr_urls = state.get("pr_urls", {})
    for name, url in pr_urls.items():
        if url:
            typer.echo(f"  {name}: {url}")


@release_app.command()
def resume():
    """Continue from last checkpoint."""
    state = load_state()
    if state is None:
        typer.echo("No active release to resume.")
        raise typer.Exit(1)
    typer.echo("Resuming release...")
    if state.get("narrative"):
        typer.echo(f"\n{state['narrative'].strip()}\n")
    phases = state.get("phases", {})
    for phase_name, phase_data in phases.items():
        if phase_data.get("status") == "pending":
            typer.echo(f"Next pending phase: {phase_name}")
            break


@release_app.command(name="list")
def list_releases():
    """Show all releases with status and staleness."""
    from datetime import datetime, timezone

    base = Path.home() / ".ovms-release" / "openvino_model_server"
    if not base.exists():
        typer.echo("No releases found.")
        raise typer.Exit(0)
    typer.echo("Active releases:")
    for version_dir in sorted(base.iterdir()):
        state_file = version_dir / "release-state.yaml"
        if state_file.exists():
            state = load_state(state_file)
            if state:
                started = state.get("started_at", "unknown")
                started_by = state.get("started_by", "unknown")
                status_val = state.get("status", "unknown")
                mtime = datetime.fromtimestamp(state_file.stat().st_mtime, tz=timezone.utc)
                age_days = (datetime.now(tz=timezone.utc) - mtime).days
                stale = " — STALE" if age_days > 30 else ""
                typer.echo(f"  {version_dir.name}  started {started} by {started_by}  {status_val}{stale}")


@release_app.command()
def notes(version: Optional[str] = typer.Option(None, "--version", "-v")):
    """Generate release notes from state data."""
    rc = _run_script("generate-release-notes.sh", [version] if version else [])
    raise typer.Exit(rc)


@release_app.command()
def audit(version: Optional[str] = typer.Option(None, "--version", "-v")):
    """Generate compliance audit report from state."""
    rc = _run_script("generate-audit-report.sh", [version] if version else [])
    raise typer.Exit(rc)


@release_app.command()
def abort(reason: Optional[str] = typer.Option(None, "--reason", "-r")):
    """Abort current release with cleanup."""
    from datetime import datetime, timezone

    state = load_state()
    if state is None:
        typer.echo("No active release to abort.")
        raise typer.Exit(1)
    if not reason:
        reason = typer.prompt("Reason for abort")
    state["aborted_at"] = datetime.now(tz=timezone.utc).isoformat()
    state["abort_reason"] = reason
    state["status"] = "aborted"
    save_state(state)
    typer.echo(f"Release aborted: {reason}")
    pr_urls = state.get("pr_urls", {})
    open_prs = {k: v for k, v in pr_urls.items() if v}
    if open_prs:
        typer.echo("\nOpen PRs from this release:")
        for name, url in open_prs.items():
            typer.echo(f"  {name}: {url}")
        typer.echo("\nClose these PRs manually if needed.")


# --- Standalone utility apps ---

diff_app = typer.Typer(name="ovms-release-diff", help="Diff between two OVMS releases.", no_args_is_help=True)


@diff_app.command()
def diff_main(
    v1: str = typer.Argument(..., help="First version"),
    v2: str = typer.Argument(..., help="Second version"),
):
    """Compare two OVMS releases (ARG changes, commit delta, dep versions)."""
    rc = _run_script("diff-args.sh", [v1, v2])
    raise typer.Exit(rc)


rebuild_app = typer.Typer(name="ovms-release-rebuild", help="Trigger CVE rebuild.", no_args_is_help=True)


@rebuild_app.command()
def rebuild_main(branch: Optional[str] = typer.Option(None, "--branch", "-b")):
    """Trigger CVE rebuild via PR to downstream."""
    args = ["--branch", branch] if branch else []
    rc = _run_script("cherry-pick.sh", args)
    raise typer.Exit(rc)


hotfix_app = typer.Typer(name="ovms-release-hotfix", help="Cherry-pick hotfix.", no_args_is_help=True)


@hotfix_app.command()
def hotfix_main(
    sha: str = typer.Argument(..., help="Commit SHA to cherry-pick"),
    branch: str = typer.Argument(..., help="Target branch"),
):
    """Cherry-pick a commit to an older release branch."""
    rc = _run_script("cherry-pick.sh", [sha, branch])
    raise typer.Exit(rc)


patch_app = typer.Typer(name="ovms-release-patch", help="Diagnose/regenerate patches.", no_args_is_help=True)


@patch_app.command()
def patch_main(version: str = typer.Argument(..., help="Release version")):
    """Diagnose and regenerate failing OVMS patches."""
    rc = _run_script("patch-update.sh", [version])
    raise typer.Exit(rc)


e2e_app = typer.Typer(name="ovms-release-e2e", help="Run E2E validation.", no_args_is_help=True)


@e2e_app.command()
def e2e_main(
    image_url: Optional[str] = typer.Argument(None, help="OVMS image URL to test"),
    from_state: bool = typer.Option(False, "--from-state", help="Auto-detect image from release state"),
    smoke_only: bool = typer.Option(False, "--smoke-only", help="Run quick smoke tests only"),
    test_filter: Optional[str] = typer.Option(None, "--test-filter", help="pytest -k filter"),
    test_path: Optional[str] = typer.Option(None, "--test-path", help="Override test path"),
):
    """Run opendatahub-tests E2E validation against an OVMS image."""
    args = []
    if image_url:
        args.extend(["--image", image_url])
    if from_state:
        args.append("--from-state")
    if smoke_only:
        args.append("--smoke-only")
    if test_filter:
        args.extend(["--test-filter", test_filter])
    if test_path:
        args.extend(["--test-path", test_path])
    rc = _run_script("run-e2e-tests.sh", args)
    raise typer.Exit(rc)
