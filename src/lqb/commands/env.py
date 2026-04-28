from __future__ import annotations

from typing import Optional

import typer

from lqb.config import profiles as cfg_mod
from lqb.config.schema import Config, Profile
from lqb.ui import prompts, tables
from lqb.utils.secrets import delete_password, get_password, set_password

app = typer.Typer(help="Manage connection profiles.")


def prompt_new_profile(cfg: Config | None = None) -> tuple[Profile, str]:
    """Prompt for all profile fields. If cfg is given, check for duplicates early."""
    name = prompts.text("Profile name (e.g. local-pg, staging):")
    if not name:
        tables.err("Name required.")
        raise typer.Exit(1)
    if cfg is not None and cfg.get(name):
        tables.err(f"Profile '{name}' already exists. Delete first or choose another name.")
        raise typer.Exit(1)
    jdbc_url = prompts.text("JDBC URL (e.g. jdbc:postgresql://localhost:5432/mydb):")
    username = prompts.text("Username:")
    password = prompts.password("Password (stored in OS keychain):")
    changelog_file = prompts.text("Changelog file path (e.g. db/changelog.xml):")
    default_schema = prompts.text("Default schema (leave blank for default):")
    protected = prompts.confirm("Mark as PROTECTED (requires extra confirmation for destructive ops)?")
    profile = Profile(
        name=name,
        jdbc_url=jdbc_url,
        username=username,
        changelog_file=changelog_file,
        default_schema=default_schema or None,
        protected=protected,
    )
    return profile, password


def register_profile(cfg: Config, profile: Profile, password: str, *, set_active: bool = True) -> None:
    """Append profile to cfg, store password in keychain, and save."""
    cfg.profiles.append(profile)
    if set_active and cfg.active is None:
        cfg.active = profile.name
    set_password(profile.name, password)
    cfg_mod.save(cfg)


@app.command("list")
def env_list() -> None:
    """List all profiles."""
    cfg = cfg_mod.load()
    if not cfg.profiles:
        tables.info("No profiles. Run [bold]lqb env add[/bold].")
        return
    tables.console.print(tables.profiles_table(cfg.profiles, cfg.active))


@app.command("add")
def env_add() -> None:
    """Add a new profile interactively."""
    cfg = cfg_mod.load()
    profile, password = prompt_new_profile(cfg)
    register_profile(cfg, profile, password)
    tables.ok(f"Profile '{profile.name}' added.")
    if cfg.active == profile.name:
        tables.info(f"'{profile.name}' set as active profile.")


@app.command("use")
def env_use(name: str = typer.Argument(..., help="Profile name")) -> None:
    """Set active profile."""
    cfg = cfg_mod.load()
    if not cfg.get(name):
        tables.err(f"Profile '{name}' not found.")
        raise typer.Exit(1)
    cfg.active = name
    cfg_mod.save(cfg)
    tables.ok(f"Active profile → '{name}'.")


@app.command("remove")
def env_remove(name: str = typer.Argument(..., help="Profile name")) -> None:
    """Remove a profile."""
    cfg = cfg_mod.load()
    profile = cfg.get(name)
    if not profile:
        tables.err(f"Profile '{name}' not found.")
        raise typer.Exit(1)
    if not prompts.confirm(f"Delete profile '{name}'?"):
        raise typer.Exit(0)
    cfg.profiles = [p for p in cfg.profiles if p.name != name]
    if cfg.active == name:
        cfg.active = cfg.profiles[0].name if cfg.profiles else None
    delete_password(name)
    cfg_mod.save(cfg)
    tables.ok(f"Profile '{name}' removed.")


@app.command("test")
def env_test(name: Optional[str] = typer.Argument(None, help="Profile name (default: active)")) -> None:
    """Test DB connection for a profile."""
    from lqb.runner import liquibase as lqb_runner
    cfg = cfg_mod.load()
    profile = cfg.get(name) if name else cfg.active_profile()
    if not profile:
        tables.err("No profile found.")
        raise typer.Exit(1)
    tables.info(f"Testing '{profile.name}' -> {profile.jdbc_url} ...")
    result = lqb_runner.run_no_changelog(profile, "history")
    combined = result.stdout + result.stderr
    if result.ok or "databasechangelog" in combined.lower() or "no migrations" in combined.lower() or "history" in combined.lower():
        tables.ok(f"Connection to '{profile.name}' succeeded.")
    else:
        tables.runner_error_panel(result)
        raise typer.Exit(1)
