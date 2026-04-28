from __future__ import annotations

from typing import Optional

import typer

from lqb.config import profiles as cfg_mod
from lqb.runner import liquibase as lqb_runner
from lqb.ui import prompts, tables

app = typer.Typer(help="Interactive guided command builder.")

COMMANDS = ["update", "rollback", "status", "tag", "diff", "validate", "history"]


@app.callback(invoke_without_command=True)
def guided(
    env: Optional[str] = typer.Option(None, "--env", "-e"),
) -> None:
    """Walk through a Liquibase command interactively."""
    cfg = cfg_mod.load()
    profile = cfg_mod.resolve_profile(cfg, env)
    tables.info(f"Profile: [bold]{profile.name}[/bold] ({profile.jdbc_url})")

    cmd = prompts.select("Which command?", COMMANDS)
    if cmd is None:
        raise typer.Exit(0)

    extra: list[str] = []
    subcmd = cmd

    if cmd == "update":
        do_count = prompts.confirm("Apply only N changesets?", default=False)
        if do_count:
            n = prompts.text("How many?", default="1")
            subcmd = "update-count"
            extra = [n]
        ctx = prompts.text("Contexts (blank = all):")
        if ctx:
            extra.append(f"--contexts={ctx}")

    elif cmd == "rollback":
        mode = prompts.select("Rollback by:", ["count", "tag"])
        if mode == "count":
            n = prompts.text("How many changesets to roll back?", default="1")
            subcmd = "rollback-count"
            extra = [n]
        else:
            tag = prompts.text("Tag name:")
            subcmd = "rollback"
            extra = [tag]

    elif cmd == "tag":
        tag = prompts.text("Tag name:")
        extra = [tag]

    elif cmd == "diff":
        ref_url = prompts.text("Reference JDBC URL:")
        ref_user = prompts.text("Reference username:")
        ref_pwd = prompts.password("Reference password:")
        extra = [
            f"--reference-url={ref_url}",
            f"--reference-username={ref_user}",
        ]
        import os
        os.environ["LIQUIBASE_COMMAND_REFERENCE_PASSWORD"] = ref_pwd

    preview = prompts.confirm("Preview SQL before executing?", default=True)
    if preview and subcmd in ("update", "update-count", "rollback", "rollback-count"):
        sql_subcmd = subcmd + "-sql"
        tables.info("SQL preview:")
        prev = lqb_runner.run(profile, sql_subcmd, extra)
        if prev.ok:
            from rich.syntax import Syntax
            tables.console.print(Syntax(prev.stdout, "sql", theme="monokai"))
        else:
            tables.runner_error_panel(prev)

    lqb_binary = "liquibase"
    full_cmd = (
        f"{lqb_binary} --url=... --username={profile.username} "
        f"--changelog-file={profile.changelog_file} {subcmd} {' '.join(extra)}"
    )
    tables.console.print(f"\n[bold]Resolved command:[/bold] [dim]{full_cmd}[/dim]")

    if not prompts.confirm("Execute?", default=True):
        tables.info("Aborted.")
        raise typer.Exit(0)

    if profile.protected:
        if not prompts.confirm_protected(profile.name):
            tables.info("Aborted.")
            raise typer.Exit(0)

    result = lqb_runner.run(profile, subcmd, extra)
    if result.ok:
        tables.ok("Done.")
        tables.console.print(result.stdout.strip())
    else:
        tables.runner_error_panel(result)
        raise typer.Exit(1)
