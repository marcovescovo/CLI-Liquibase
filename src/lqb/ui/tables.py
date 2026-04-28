from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console(highlight=False, legacy_windows=False)
err_console = Console(stderr=True, highlight=False, legacy_windows=False)


def err(msg: str) -> None:
    err_console.print(f"[bold red]Error:[/bold red] {msg}")


def warn(msg: str) -> None:
    console.print(f"[yellow]Warning:[/yellow] {msg}")


def ok(msg: str) -> None:
    console.print(f"[green]OK[/green] {msg}")


def info(msg: str) -> None:
    console.print(f"[cyan]i[/cyan] {msg}")


def runner_error_panel(result) -> None:
    console.print(
        Panel(
            result.stderr.strip() or result.stdout.strip(),
            title="[bold red]Liquibase Error[/bold red]",
            border_style="red",
        )
    )


def profiles_table(profiles, active: str | None) -> Table:
    t = Table(title="Profiles", show_lines=True)
    t.add_column("Name", style="bold")
    t.add_column("JDBC URL")
    t.add_column("User")
    t.add_column("Protected")
    t.add_column("Active")
    for p in profiles:
        is_active = "*" if p.name == active else ""
        protected = "[red]YES[/red]" if p.protected else "no"
        t.add_row(p.name, p.jdbc_url, p.username, protected, is_active)
    return t


def changesets_table(changesets) -> Table:
    t = Table(title="Applied Changesets", show_lines=True)
    t.add_column("#", justify="right")
    t.add_column("ID")
    t.add_column("Author")
    t.add_column("Executed")
    for c in changesets:
        t.add_row(str(c.order_executed), c.id, c.author, c.date_executed)
    return t
