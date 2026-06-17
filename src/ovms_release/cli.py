"""Typer-based CLI with multiple entry points for OVMS release automation."""

from __future__ import annotations

from datetime import datetime, timezone

import typer

from ovms_release.context import ReleaseContext
from ovms_release.ops import diff_args as diff_args_mod
from ovms_release.ops import e2e as e2e_mod
from ovms_release.ops import hotfix as hotfix_mod
from ovms_release.ops import mirror as mirror_mod
from ovms_release.ops import notes as notes_mod
from ovms_release.ops import owners as owners_mod
from ovms_release.ops import patches as patches_mod
from ovms_release.ops import preflight as preflight_mod
from ovms_release.ops import rebuild as rebuild_mod
from ovms_release.ops import sync_rhoai as sync_rhoai_mod
from ovms_release.ops import sync_stable as sync_stable_mod
from ovms_release.state import DEFAULT_STATE_DIR, load_state, save_state

release_app = typer.Typer(
    name="ovms-release",
    help="OVMS release automation CLI with pre-flight intelligence and stateful tracking.",
    no_args_is_help=True,
)


def _make_ctx(
    version: str,
    *,
    dry_run: bool = False,
    rhoai_version: str = "",
) -> ReleaseContext:
    return ReleaseContext(version=version, dry_run=dry_run, rhoai_version=rhoai_version)


@release_app.command()
def preflight(
    version: str | None = typer.Argument(None, help="Release version (e.g., 2026.2)"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Phase 0: Gather intelligence and produce Release Brief."""
    if version is None:
        releases = preflight_mod.detect_upstream_releases()
        if releases:
            typer.echo("New upstream releases available:")
            for r in releases:
                typer.echo(f"  {r}")
        else:
            typer.echo("All upstream releases are already mirrored.")
        raise typer.Exit(0)

    ctx = _make_ctx(version, dry_run=dry_run)
    try:
        preflight_mod.run_preflight(ctx)
    except preflight_mod.PreflightError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1) from None


@release_app.command()
def mirror(
    version: str = typer.Argument(..., help="Release version"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    validate_only: bool = typer.Option(False, "--validate"),
) -> None:
    """Phase 1: Create mirror branches in 4 ODH repos."""
    ctx = _make_ctx(version, dry_run=dry_run)
    try:
        results = mirror_mod.mirror_branches(ctx, validate_only=validate_only)
        for repo, status in results.items():
            typer.echo(f"  {repo}: {status}")
    except mirror_mod.MirrorError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1) from None


@release_app.command()
def owners(
    version: str = typer.Argument(..., help="Release version"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Phase 2: Push OWNERS file via PR."""
    ctx = _make_ctx(version, dry_run=dry_run)
    pr_url = owners_mod.push_owners(ctx)
    if pr_url:
        typer.echo(f"PR created: {pr_url}")
    else:
        typer.echo("OWNERS file already up to date or dry-run.")


@release_app.command(name="diff-args")
def diff_args(
    version: str = typer.Argument(..., help="Release version"),
    old_version: str | None = typer.Option(None, "--old-version"),
) -> None:
    """Phase 3: ARG diff report between releases."""
    ctx = _make_ctx(version)
    try:
        result = diff_args_mod.diff_args(ctx, old_version=old_version)
        if result.added:
            typer.echo("NEW:")
            for k, v in result.added.items():
                typer.echo(f"  {k}={v}")
        if result.removed:
            typer.echo("REMOVED:")
            for k, v in result.removed.items():
                typer.echo(f"  {k}={v}")
        if result.changed:
            typer.echo("CHANGED:")
            for k, (old, new) in result.changed.items():
                typer.echo(f"  {k}: {old} -> {new}")
        if not result.added and not result.removed and not result.changed:
            typer.echo("No ARG changes.")
    except diff_args_mod.ArgDiffError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1) from None


@release_app.command(name="ci-config")
def ci_config(
    version: str = typer.Argument(..., help="Release version"),
) -> None:
    """Phase 4: Generate openshift/release CI config."""
    from ovms_release.ops import ci_config as ci_config_mod

    ctx = _make_ctx(version)
    content = ci_config_mod.generate_ci_config(ctx)
    typer.echo(content)


@release_app.command()
def patch(
    version: str = typer.Argument(..., help="Release version"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Phase 5: Apply patches and create PR."""
    ctx = _make_ctx(version, dry_run=dry_run)
    try:
        pr_url = patches_mod.apply_patches(ctx)
        if pr_url:
            typer.echo(f"PR created: {pr_url}")
        else:
            typer.echo("Dry run complete.")
    except patches_mod.PatchError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1) from None


@release_app.command(name="sync-stable")
def sync_stable(
    version: str = typer.Argument(..., help="Release version"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Phase 6: Tree transplant merge to stable branch."""
    ctx = _make_ctx(version, dry_run=dry_run)
    result = sync_stable_mod.tree_transplant(ctx)
    if result.needs_confirm:
        typer.echo("Untracked files detected after merge:")
        for f in result.untracked_files:
            typer.echo(f"  {f}")
        if typer.confirm("Remove these files and proceed?"):
            result = sync_stable_mod.tree_transplant(ctx, confirm_clean=True)
        else:
            raise typer.Abort()
    if result.pr_url:
        typer.echo(f"PR created: {result.pr_url}")
    elif result.success:
        typer.echo("Sync complete.")


@release_app.command(name="sync-rhoai")
def sync_rhoai(
    version: str = typer.Argument(..., help="Release version"),
    rhoai_version: str = typer.Option(..., "--rhoai-version", help="RHOAI target version"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Phase 7: Sync stable to rhoai branch."""
    from ovms_release.context import EmptySyncError

    ctx = _make_ctx(version, dry_run=dry_run, rhoai_version=rhoai_version)
    try:
        pr_url = sync_rhoai_mod.sync_to_rhoai(ctx)
        if pr_url:
            typer.echo(f"PR created: {pr_url}")
        else:
            typer.echo("Dry run complete.")
    except EmptySyncError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1) from None


@release_app.command()
def status() -> None:
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
def resume() -> None:
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
def list_releases() -> None:
    """Show all releases with status and staleness."""
    base = DEFAULT_STATE_DIR
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
def notes(
    version: str = typer.Argument(..., help="Release version"),
) -> None:
    """Generate release notes from state data."""
    ctx = _make_ctx(version)
    output = notes_mod.generate_notes(ctx)
    typer.echo(f"Notes written to: {output}")


@release_app.command()
def audit(
    version: str = typer.Argument(..., help="Release version"),
) -> None:
    """Generate compliance audit report from state."""
    ctx = _make_ctx(version)
    output = notes_mod.generate_audit(ctx)
    typer.echo(f"Audit report written to: {output}")


@release_app.command()
def abort(reason: str | None = typer.Option(None, "--reason", "-r")) -> None:
    """Abort current release with cleanup."""
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
) -> None:
    """Compare two OVMS releases (ARG changes, commit delta, dep versions)."""
    ctx = _make_ctx(v2)
    result = diff_args_mod.diff_args(ctx, old_version=v1)
    if result.changed:
        for k, (old, new) in result.changed.items():
            typer.echo(f"  {k}: {old} -> {new}")


rebuild_app = typer.Typer(name="ovms-release-rebuild", help="Trigger CVE rebuild.", no_args_is_help=True)


@rebuild_app.command()
def rebuild_main(
    branch: str = typer.Option(..., "--branch", "-b", help="Target branch"),
    bump_base: bool = typer.Option(False, "--bump-base"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Trigger CVE rebuild via PR to downstream."""
    ctx = _make_ctx("0.0", dry_run=dry_run)
    try:
        pr_url = rebuild_mod.cve_rebuild(ctx, branch, bump_base=bump_base)
        if pr_url:
            typer.echo(f"PR created: {pr_url}")
        else:
            typer.echo("Dry run complete.")
    except rebuild_mod.RebuildError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1) from None


hotfix_app = typer.Typer(name="ovms-release-hotfix", help="Cherry-pick hotfix.", no_args_is_help=True)


@hotfix_app.command()
def hotfix_main(
    sha: str = typer.Argument(..., help="Commit SHA to cherry-pick"),
    branch: str = typer.Argument(..., help="Target branch"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    """Cherry-pick a commit to an older release branch."""
    ctx = _make_ctx("0.0", dry_run=dry_run)
    try:
        pr_url = hotfix_mod.cherry_pick(ctx, sha, branch)
        if pr_url:
            typer.echo(f"PR created: {pr_url}")
        else:
            typer.echo("Already present or dry-run.")
    except hotfix_mod.HotfixError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1) from None


patch_app = typer.Typer(name="ovms-release-patch", help="Diagnose/regenerate patches.", no_args_is_help=True)


@patch_app.command()
def patch_main(version: str = typer.Argument(..., help="Release version")) -> None:
    """Diagnose and regenerate failing OVMS patches."""
    ctx = _make_ctx(version)
    failures = patches_mod.diagnose_patches(ctx)
    if failures:
        typer.echo("Failed patches:")
        for p, err in failures.items():
            typer.echo(f"  {p}: {err}")
    else:
        typer.echo("All patches apply cleanly.")


e2e_app = typer.Typer(name="ovms-release-e2e", help="Run E2E validation.", no_args_is_help=True)


@e2e_app.command()
def e2e_main(
    image_url: str = typer.Argument(..., help="OVMS image URL to test"),
    smoke_only: bool = typer.Option(False, "--smoke-only"),
    test_filter: str | None = typer.Option(None, "--test-filter"),
    test_path: str | None = typer.Option(None, "--test-path"),
) -> None:
    """Run opendatahub-tests E2E validation against an OVMS image."""
    ctx = _make_ctx("0.0")
    try:
        e2e_mod.run_e2e(
            ctx,
            image_url,
            smoke_only=smoke_only,
            test_filter=test_filter or "",
            test_path=test_path or "tests/model_serving/model_runtime/openvino/",
        )
    except e2e_mod.E2EError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1) from None
