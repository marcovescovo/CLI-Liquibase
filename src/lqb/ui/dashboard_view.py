from __future__ import annotations

import time
from typing import Callable

from rich import box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def _render(data: dict, console: Console) -> Table:
    pending = data["pending"]
    locks = data["locks"]
    changesets = data["changesets"]

    # ── status line ──────────────────────────────────────────────────────────
    if pending == -1:
        pending_str = "[dim]N/A (changelog not found in working dir)[/dim]"
    elif pending == 0:
        pending_str = "[green]OK  No pending changesets[/green]"
    else:
        pending_str = f"[yellow]!!  {pending} pending changeset(s)[/yellow]"

    locked_any = any(lk.locked for lk in locks)
    if locked_any:
        parts = [f"[red]LOCKED by {lk.locked_by or 'unknown'}[/red]" for lk in locks if lk.locked]
        lock_str = "  ".join(parts)
    else:
        lock_str = "[green]UNLOCKED[/green]"

    # ── history table ─────────────────────────────────────────────────────────
    hist = Table(box=box.SIMPLE_HEAD, show_header=True, expand=True, padding=(0, 1))
    hist.add_column("#", justify="right", style="dim", width=4, no_wrap=True)
    hist.add_column("Changeset ID", no_wrap=True)
    hist.add_column("Author", no_wrap=True)
    hist.add_column("File", no_wrap=False)
    hist.add_column("Executed", style="dim", no_wrap=True)
    for c in changesets[-20:]:
        hist.add_row(str(c.order_executed), c.id, c.author, c.filepath, c.date_executed)

    # ── outer wrapper ─────────────────────────────────────────────────────────
    header = (
        f"[bold]{data['profile_name']}[/bold]  [dim]{data['jdbc_url']}[/dim]\n"
        f"Pending: {pending_str}    Locks: {lock_str}"
    )

    return Panel(
        Panel(hist, title="[bold]Applied Changesets (last 20)[/bold]", border_style="blue"),
        title=header,
        border_style="cyan",
        subtitle="[dim]Ctrl+C to quit[/dim]",
    )


def run_dashboard(fetch: Callable, refresh_seconds: int = 5) -> None:
    console = Console(highlight=False, legacy_windows=False)
    console.print("[dim]Loading dashboard...[/dim]")
    try:
        with Live(console=console, refresh_per_second=4, screen=True) as live:
            while True:
                data = fetch()
                live.update(_render(data, console))
                time.sleep(refresh_seconds)
    except KeyboardInterrupt:
        pass
    console.print("[dim]Dashboard closed.[/dim]")
