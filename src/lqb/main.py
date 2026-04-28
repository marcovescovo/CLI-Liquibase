from __future__ import annotations

import shutil

import typer
from rich.console import Console

from lqb.commands import dashboard, env, guided, init, rollback, status, update, validate

console = Console()

app = typer.Typer(
    name="lqb",
    help="Liquibase assistant CLI. Run [bold]lqb --help[/bold] for commands.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

app.add_typer(env.app, name="env")
app.add_typer(init.app, name="init")
app.add_typer(status.app, name="status")
app.add_typer(update.app, name="update")
app.add_typer(rollback.app, name="rollback")
app.add_typer(validate.app, name="validate")
app.add_typer(dashboard.app, name="dash")
app.add_typer(guided.app, name="do")


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-V", is_eager=True, help="Show version"),
) -> None:
    if version:
        console.print("lqb 0.1.0")
        raise typer.Exit()
    if ctx.invoked_subcommand not in ("env",) and not shutil.which("liquibase"):
        console.print(
            "[bold red]Error:[/bold red] [bold]liquibase[/bold] binary not found on PATH.\n"
            "Install from [link]https://www.liquibase.org/download[/link]"
        )
        raise typer.Exit(1)
