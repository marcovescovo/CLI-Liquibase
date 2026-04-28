from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import typer

from lqb.config import profiles as cfg_mod
from lqb.runner import liquibase as lqb_runner
from lqb.runner.parser import parse_validate
from lqb.ui import tables

app = typer.Typer(help="Validate and lint changelog.")


def _extra_lint(changelog_path: str) -> list[str]:
    issues: list[str] = []
    p = Path(changelog_path)
    if not p.exists():
        return [f"Changelog file not found: {changelog_path}"]
    suffix = p.suffix.lower()
    if suffix in (".xml",):
        try:
            tree = ET.parse(p)
            root = tree.getroot()
            ns = {"lb": "http://www.liquibase.org/xml/ns/dbchangelog"}
            seen_ids: set[str] = set()
            for cs in root.iter():
                if cs.tag.endswith("changeSet"):
                    cs_id = cs.get("id", "")
                    author = cs.get("author", "")
                    if not author:
                        issues.append(f"changeSet id='{cs_id}' missing author")
                    key = f"{cs_id}::{author}"
                    if key in seen_ids:
                        issues.append(f"Duplicate changeSet id='{cs_id}' author='{author}'")
                    seen_ids.add(key)
        except ET.ParseError as e:
            issues.append(f"XML parse error: {e}")
    return issues


@app.callback(invoke_without_command=True)
def validate(
    env: Optional[str] = typer.Option(None, "--env", "-e"),
    lint_only: bool = typer.Option(False, "--lint-only", help="Local lint only, no liquibase call"),
) -> None:
    """Validate changelog via Liquibase + extra lint checks."""
    cfg = cfg_mod.load()
    profile = cfg_mod.resolve_profile(cfg, env)

    lint_issues = _extra_lint(profile.changelog_file)
    if lint_issues:
        tables.console.print("[yellow]Lint issues:[/yellow]")
        for i in lint_issues:
            tables.console.print(f"  [yellow]-[/yellow] {i}")
    else:
        tables.ok("Local lint passed.")

    if lint_only:
        return

    tables.info("Running liquibase validate …")
    result = lqb_runner.run(profile, "validate")
    ok, issues = parse_validate(result.stdout + result.stderr)
    if ok:
        tables.ok("Liquibase validation passed.")
    else:
        tables.console.print("[red]Validation issues:[/red]")
        for i in issues:
            tables.console.print(f"  [red]-[/red] {i}")
        if not result.ok:
            tables.runner_error_panel(result)
            raise typer.Exit(1)
