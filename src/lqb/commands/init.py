from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Optional

import typer

from lqb.commands.env import prompt_new_profile, register_profile
from lqb.config import profiles as cfg_mod
from lqb.config.schema import Config, Profile
from lqb.runner import liquibase as lqb_runner
from lqb.ui import prompts, tables
from lqb.utils.secrets import get_password

app = typer.Typer(help="Bootstrap a Liquibase project (greenfield or brownfield).")

_MASTER_GREENFIELD = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <databaseChangeLog
        xmlns="http://www.liquibase.org/xml/ns/dbchangelog"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.liquibase.org/xml/ns/dbchangelog
        http://www.liquibase.org/xml/ns/dbchangelog/dbchangelog-4.0.xsd">

        <!-- Add changesets by including files from changes/ -->
        <!-- Example: <include file="changes/001-initial.xml" relativeToChangelogFile="true"/> -->

    </databaseChangeLog>
""")

_MASTER_BROWNFIELD = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <databaseChangeLog
        xmlns="http://www.liquibase.org/xml/ns/dbchangelog"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.liquibase.org/xml/ns/dbchangelog
        http://www.liquibase.org/xml/ns/dbchangelog/dbchangelog-4.0.xsd">

        <include file="baseline.xml" relativeToChangelogFile="true"/>
        <!-- Add future changesets here -->
        <!-- Example: <include file="changes/001-add-users.xml" relativeToChangelogFile="true"/> -->

    </databaseChangeLog>
""")


def _resolve_or_create_profile(cfg: Config) -> tuple[Profile, str | None]:
    """Return (profile, password). Password is None for existing profiles."""
    if cfg.profiles:
        choices = [p.name for p in cfg.profiles] + ["[+ create new profile]"]
        choice = prompts.select("Select profile:", choices)
        if choice != "[+ create new profile]":
            return cfg.get(choice), None  # type: ignore[return-value]
    profile, pwd = prompt_new_profile()
    return profile, pwd


def _finalize_profile(cfg: Config, profile: Profile, pwd: str | None, changelog_path: str) -> None:
    """Set changelog_file on profile and persist. Registers new profiles via keychain."""
    updated = profile.model_copy(update={"changelog_file": changelog_path})
    if cfg.get(updated.name) is None:
        register_profile(cfg, updated, pwd)  # type: ignore[arg-type]
    else:
        cfg.profiles = [updated if p.name == updated.name else p for p in cfg.profiles]
        cfg_mod.save(cfg)
    tables.ok(f"Profile '{updated.name}' changelog_file → {changelog_path}")


def _greenfield(root: Path, profile: Profile, cfg: Config, pwd: str | None, yes: bool) -> None:
    master = root / "db.changelog-master.xml"
    changes = root / "changes"

    if master.exists() and not yes:
        if not prompts.confirm(f"{master} already exists. Overwrite?"):
            raise typer.Exit(0)

    root.mkdir(parents=True, exist_ok=True)
    changes.mkdir(parents=True, exist_ok=True)
    (changes / ".gitkeep").touch()
    master.write_text(_MASTER_GREENFIELD, encoding="utf-8")

    tables.ok(f"Created {master}")
    tables.ok(f"Created {changes}/")

    _finalize_profile(cfg, profile, pwd, str(master))

    tables.console.print("\n[bold]Next steps:[/bold]")
    tables.console.print(f"  1. Add changeset files in [cyan]{changes}/[/cyan]")
    tables.console.print(f"  2. Include them in [cyan]{master}[/cyan]")
    tables.console.print("  3. [bold]lqb status[/bold]        — check pending changesets")
    tables.console.print("  4. [bold]lqb update --preview[/bold]  — preview SQL before applying")
    tables.console.print("  5. [bold]lqb update[/bold]           — apply migrations")


def _brownfield(root: Path, profile: Profile, cfg: Config, pwd: str | None, yes: bool) -> None:
    master = root / "db.changelog-master.xml"
    baseline = root / "baseline.xml"

    root.mkdir(parents=True, exist_ok=True)

    tables.console.print(
        f"\n[bold yellow]Brownfield init[/bold yellow] — will run "
        f"[bold]generate-changelog[/bold] on:\n"
        f"  URL:    [cyan]{profile.jdbc_url}[/cyan]\n"
        f"  User:   [cyan]{profile.username}[/cyan]\n"
        f"  Output: [cyan]{baseline}[/cyan]\n"
    )
    if not yes and not prompts.confirm("Proceed?", default=True):
        raise typer.Exit(0)

    password = pwd if pwd is not None else get_password(profile.name)

    tables.info("Running generate-changelog …")
    result = lqb_runner.run_no_changelog(
        profile,
        "generate-changelog",
        extra_args=[f"--changelog-file={baseline}"],
        password=password,
    )
    if not result.ok:
        tables.runner_error_panel(result)
        raise typer.Exit(1)
    tables.ok(f"baseline.xml generated → {baseline}")

    preview = baseline.read_text(encoding="utf-8")[:1200]
    tables.console.print(f"\n[dim]{preview}\n… (truncated)[/dim]\n")

    if not prompts.confirm("Review complete. Run changelog-sync to mark baseline as applied?", default=True):
        tables.warn("Aborted. baseline.xml left on disk; changelog-sync NOT run.")
        raise typer.Exit(0)

    tables.info("Running changelog-sync …")
    result = lqb_runner.run_no_changelog(
        profile,
        "changelog-sync",
        extra_args=[f"--changelog-file={baseline}"],
        password=password,
    )
    if not result.ok:
        tables.runner_error_panel(result)
        raise typer.Exit(1)
    tables.ok("changelog-sync complete — baseline marked as applied.")

    if master.exists() and not yes:
        if not prompts.confirm(f"{master} already exists. Overwrite?"):
            raise typer.Exit(0)
    master.write_text(_MASTER_BROWNFIELD, encoding="utf-8")
    tables.ok(f"Created {master} (includes baseline.xml)")

    _finalize_profile(cfg, profile, pwd, str(master))

    tables.warn("baseline.xml = snapshot of current schema, NOT reproducible from scratch.")
    tables.console.print("[bold]Next steps:[/bold]")
    tables.console.print(f"  1. Add future changeset files and include them in [cyan]{master}[/cyan]")
    tables.console.print("  2. [bold]lqb status[/bold]  — should show 0 pending changesets")


@app.callback(invoke_without_command=True)
def init_cmd(
    env: Optional[str] = typer.Option(None, "--env", "-e", help="Profile to use (skips profile selection)"),
    path: Optional[str] = typer.Option(None, "--path", help="Changelog root directory (default: db/changelog)"),
    mode: Optional[str] = typer.Option(None, "--mode", help="greenfield or brownfield (skips prompt)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip non-destructive confirmations"),
) -> None:
    """Bootstrap a Liquibase project (greenfield or brownfield)."""
    tables.console.print("[bold cyan]lqb init[/bold cyan] — Liquibase project bootstrap\n")

    selected_mode = mode
    if selected_mode not in ("greenfield", "brownfield"):
        raw = prompts.select(
            "Project type:",
            choices=[
                "greenfield  — empty DB, scaffold changelog structure",
                "brownfield  — existing DB, generate baseline from schema",
            ],
        )
        selected_mode = "greenfield" if raw.startswith("greenfield") else "brownfield"

    cfg = cfg_mod.load()

    if env:
        profile = cfg.get(env)
        if not profile:
            tables.err(f"Profile '{env}' not found.")
            raise typer.Exit(1)
        pwd: str | None = None
    else:
        profile, pwd = _resolve_or_create_profile(cfg)

    default_root = path or "db/changelog"
    raw_root = prompts.text("Changelog root directory:", default=default_root)
    root = Path(raw_root or default_root)

    if selected_mode == "greenfield":
        _greenfield(root, profile, cfg, pwd, yes)
    else:
        _brownfield(root, profile, cfg, pwd, yes)
