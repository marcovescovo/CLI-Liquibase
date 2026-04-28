from __future__ import annotations

from typing import Optional

import typer

from lqb.config import profiles as cfg_mod
from lqb.runner import liquibase as lqb_runner
from lqb.ui import prompts, tables

app = typer.Typer(help="Apply pending changesets.")


@app.callback(invoke_without_command=True)
def update(
    env: Optional[str] = typer.Option(None, "--env", "-e"),
    preview: bool = typer.Option(False, "--preview", "-p", help="Show SQL without applying"),
    count: Optional[int] = typer.Option(None, "--count", "-n", help="Apply N changesets"),
    contexts: Optional[str] = typer.Option(None, "--contexts", help="Comma-separated contexts"),
    label_filter: Optional[str] = typer.Option(None, "--label-filter"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Apply pending changesets (or preview SQL)."""
    cfg = cfg_mod.load()
    profile = cfg_mod.resolve_profile(cfg, env)

    extra: list[str] = []
    if contexts:
        extra += [f"--contexts={contexts}"]
    if label_filter:
        extra += [f"--label-filter={label_filter}"]

    if preview:
        subcmd = "update-count-sql" if count else "update-sql"
        if count:
            extra = [str(count)] + extra
        tables.info(f"Preview SQL for [bold]{profile.name}[/bold]")
        result = lqb_runner.run(profile, subcmd, extra)
        if result.ok:
            from rich.syntax import Syntax
            tables.console.print(Syntax(result.stdout, "sql", theme="monokai", line_numbers=False))
        else:
            tables.runner_error_panel(result)
            raise typer.Exit(1)
        return

    if profile.protected and not yes:
        if not prompts.confirm_protected(profile.name):
            tables.info("Aborted.")
            raise typer.Exit(0)
    elif not yes:
        if not prompts.confirm(f"Apply changesets on '{profile.name}'?", default=True):
            tables.info("Aborted.")
            raise typer.Exit(0)

    subcmd = "update-count" if count else "update"
    if count:
        extra = [str(count)] + extra

    tables.info(f"Applying to [bold]{profile.name}[/bold] …")
    result = lqb_runner.run(profile, subcmd, extra)
    if result.ok:
        tables.ok("Update complete.")
        tables.console.print(result.stdout.strip())
    else:
        tables.runner_error_panel(result)
        raise typer.Exit(1)
