from __future__ import annotations

from typing import Optional

import typer

from lqb.config import profiles as cfg_mod
from lqb.runner import liquibase as lqb_runner
from lqb.runner.parser import parse_history, parse_locks, parse_status
from lqb.ui import tables
from lqb.ui.dashboard_view import run_dashboard

app = typer.Typer(help="Live status dashboard.")


@app.callback(invoke_without_command=True)
def dashboard(
    env: Optional[str] = typer.Option(None, "--env", "-e"),
    refresh: int = typer.Option(5, "--refresh", "-r", help="Refresh interval in seconds"),
) -> None:
    """Live-refresh dashboard: pending, history, locks."""
    cfg = cfg_mod.load()
    profile = cfg_mod.resolve_profile(cfg, env)
    tables.info(f"Dashboard for [bold]{profile.name}[/bold]. Ctrl+C to quit.")

    def fetch() -> dict:
        # status needs changelog — use run(); fall back gracefully if changelog missing
        status_result = lqb_runner.run(profile, "status")
        status_data = parse_status(status_result.stdout + status_result.stderr)
        pending = status_data.pending_count if status_result.ok or "changesets have not been applied" in (status_result.stdout + status_result.stderr).lower() else -1

        hist_result = lqb_runner.run_no_changelog(profile, "history")
        changesets = parse_history(hist_result.stdout) if hist_result.ok else []

        lock_result = lqb_runner.run_no_changelog(profile, "list-locks")
        locks = parse_locks(lock_result.stdout + lock_result.stderr)

        return {
            "pending": pending,
            "changesets": changesets,
            "locks": locks,
            "profile_name": profile.name,
            "jdbc_url": profile.jdbc_url,
        }

    run_dashboard(fetch, refresh_seconds=refresh)
