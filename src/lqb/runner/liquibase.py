from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ON_WINDOWS = platform.system() == "Windows"

from lqb.config.schema import Profile
from lqb.utils.secrets import get_password


@dataclass
class RunResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _resolve_password(profile_name: str, override: str | None) -> str:
    if override:
        return override
    pwd = get_password(profile_name)
    if pwd is not None:
        return pwd
    safe = profile_name.replace("-", "_").upper()
    pwd = os.environ.get(f"LQB_PASSWORD_{safe}") or os.environ.get("LQB_PASSWORD")
    if pwd is not None:
        return pwd
    non_interactive = os.environ.get("LQB_NON_INTERACTIVE") or not sys.stdin.isatty()
    if non_interactive:
        from lqb.ui.tables import err
        err(
            f"No password for profile '{profile_name}' in non-interactive mode. "
            f"Set [bold]LQB_PASSWORD_{safe}[/bold] or [bold]LQB_PASSWORD[/bold]."
        )
        raise SystemExit(1)
    import getpass
    return getpass.getpass(f"Password for profile '{profile_name}': ")


def _find_binary() -> str:
    # 1. managed install written by install.py
    env_file = Path.home() / ".lqb" / "env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("LIQUIBASE_BINARY="):
                candidate = Path(line.split("=", 1)[1].strip())
                if candidate.exists():
                    return str(candidate)

    # 2. PATH — skip liquibase-secure (Pro, needs license)
    binary = shutil.which("liquibase")
    if binary and "liquibase-secure" not in binary.lower():
        return binary

    from lqb.ui.tables import err
    err(
        "[bold]liquibase[/bold] OSS binary not found.\n"
        "Run: [bold]python install.py[/bold]"
    )
    raise SystemExit(1)


def run(
    profile: Profile,
    subcommand: str,
    extra_args: list[str] | None = None,
    password: str | None = None,
    env_extra: dict[str, str] | None = None,
) -> RunResult:
    binary = _find_binary()
    pwd = _resolve_password(profile.name, password)

    base_args = [
        binary,
        f"--url={profile.jdbc_url}",
        f"--username={profile.username}",
        f"--changelog-file={profile.changelog_file}",
    ]
    if profile.default_schema:
        base_args.append(f"--default-schema-name={profile.default_schema}")

    cmd = base_args + [subcommand] + (extra_args or [])

    env = os.environ.copy()
    env["LIQUIBASE_COMMAND_PASSWORD"] = pwd
    if env_extra:
        env.update(env_extra)

    # On Windows, prepend System32 so Windows builtins (find.exe, etc.)
    # take priority over Unix equivalents injected by Git Bash / MSYS2.
    if ON_WINDOWS:
        sys32 = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32")
        env["PATH"] = sys32 + os.pathsep + env.get("PATH", "")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        shell=ON_WINDOWS,
    )
    return RunResult(
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def run_no_changelog(
    profile: Profile,
    subcommand: str,
    extra_args: list[str] | None = None,
    password: str | None = None,
) -> RunResult:
    """Run a subcommand that doesn't require --changelog-file (e.g. history, list-locks)."""
    binary = _find_binary()
    pwd = _resolve_password(profile.name, password)

    cmd = [
        binary,
        f"--url={profile.jdbc_url}",
        f"--username={profile.username}",
        subcommand,
    ] + (extra_args or [])

    env = os.environ.copy()
    env["LIQUIBASE_COMMAND_PASSWORD"] = pwd
    if ON_WINDOWS:
        sys32 = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32")
        env["PATH"] = sys32 + os.pathsep + env.get("PATH", "")

    result = subprocess.run(cmd, capture_output=True, text=True, env=env, shell=ON_WINDOWS)
    return RunResult(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)


def check_binary() -> bool:
    return shutil.which("liquibase") is not None
