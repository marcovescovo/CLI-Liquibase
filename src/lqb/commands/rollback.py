from __future__ import annotations

from typing import Optional

import typer

from lqb.config import profiles as cfg_mod
from lqb.runner import liquibase as lqb_runner
from lqb.ui import prompts, tables

app = typer.Typer(help="Rollback changesets.")


@app.callback(invoke_without_command=True)
def rollback(
    env: Optional[str] = typer.Option(None, "--env", "-e"),
    count: Optional[int] = typer.Option(None, "--count", "-n", help="Rollback N changesets"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Rollback to tag"),
    preview: bool = typer.Option(False, "--preview", "-p", help="Show SQL without applying"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Rollback changesets by count or tag."""
    if not count and not tag:
        tables.err("Provide [bold]--count[/bold] or [bold]--tag[/bold].")
        raise typer.Exit(1)

    cfg = cfg_mod.load()
    profile = cfg_mod.resolve_profile(cfg, env)

    if preview:
        if count:
            subcmd, extra = "rollback-count-sql", [str(count)]
        else:
            subcmd, extra = "rollback-sql", [tag]
        tables.info(f"Rollback SQL preview for [bold]{profile.name}[/bold]")
        result = lqb_runner.run(profile, subcmd, extra)
        if result.ok:
            from rich.syntax import Syntax
            tables.console.print(Syntax(result.stdout, "sql", theme="monokai"))
        else:
            tables.runner_error_panel(result)
            raise typer.Exit(1)
        return

    if not yes:
        desc = f"{count} changeset(s)" if count else f"tag '{tag}'"
        msg = f"[bold red]Rollback {desc} on '{profile.name}'?[/bold red]"
        if profile.protected:
            if not prompts.confirm_protected(profile.name):
                tables.info("Aborted.")
                raise typer.Exit(0)
        else:
            if not prompts.confirm(msg):
                tables.info("Aborted.")
                raise typer.Exit(0)

    if count:
        subcmd, extra = "rollback-count", [str(count)]
    else:
        subcmd, extra = "rollback", [tag]

    tables.info(f"Rolling back on [bold]{profile.name}[/bold] …")
    result = lqb_runner.run(profile, subcmd, extra)
    if result.ok:
        tables.ok("Rollback complete.")
        tables.console.print(result.stdout.strip())
    else:
        tables.runner_error_panel(result)
        raise typer.Exit(1)
