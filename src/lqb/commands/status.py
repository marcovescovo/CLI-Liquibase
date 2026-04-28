from __future__ import annotations

from typing import Optional

import typer

from lqb.config import profiles as cfg_mod
from lqb.runner import liquibase as lqb_runner
from lqb.runner.parser import parse_history, parse_status
from lqb.ui import tables

app = typer.Typer(help="Show DB changeset status.")


@app.callback(invoke_without_command=True)
def status(
    env: Optional[str] = typer.Option(None, "--env", "-e", help="Profile name"),
) -> None:
    """Show pending and applied changesets."""
    cfg = cfg_mod.load()
    profile = cfg_mod.resolve_profile(cfg, env)
    tables.info(f"Status for [bold]{profile.name}[/bold] ({profile.jdbc_url})")

    result = lqb_runner.run(profile, "status")
    if not result.ok and "changesets have not been applied" not in result.stdout and "is up to date" not in result.stdout:
        tables.runner_error_panel(result)
        raise typer.Exit(1)

    status_data = parse_status(result.stdout + result.stderr)
    if status_data.pending_count == 0:
        tables.ok("Database is up to date.")
    else:
        tables.warn(f"{status_data.pending_count} pending changeset(s):")
        for cs in status_data.pending_changesets:
            tables.console.print(f"  [yellow]-[/yellow] {cs}")

    hist_result = lqb_runner.run(profile, "history")
    if hist_result.ok:
        changesets = parse_history(hist_result.stdout)
        if changesets:
            tables.console.print(tables.changesets_table(changesets[-10:]))
