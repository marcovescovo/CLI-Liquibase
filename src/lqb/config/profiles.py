from __future__ import annotations

import os
from pathlib import Path

import yaml

from lqb.config.schema import Config, Profile

CONFIG_DIR = Path.home() / ".lqb"
CONFIG_FILE = CONFIG_DIR / "profiles.yaml"


def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load() -> Config:
    _ensure_dir()
    if not CONFIG_FILE.exists():
        return Config()
    raw = yaml.safe_load(CONFIG_FILE.read_text()) or {}
    return Config.model_validate(raw)


def save(cfg: Config) -> None:
    _ensure_dir()
    data = cfg.model_dump(exclude_none=True)
    CONFIG_FILE.write_text(yaml.dump(data, default_flow_style=False))


def resolve_profile(cfg: Config, env_override: str | None) -> Profile:
    name = env_override or os.environ.get("LQB_ENV")
    if name:
        p = cfg.get(name)
        if not p:
            from lqb.ui.tables import err
            err(f"Profile '{name}' not found.")
            raise SystemExit(1)
        return p
    p = cfg.active_profile()
    if not p:
        from lqb.ui.tables import err
        err("No active profile. Run [bold]lqb env add[/bold] or [bold]lqb env use <name>[/bold].")
        raise SystemExit(1)
    return p
