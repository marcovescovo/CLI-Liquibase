"""
lqb installer — checks requirements and downloads missing components.

Requirements checked:
  - Python >= 3.11
  - Java >= 11 (on PATH)
  - Liquibase OSS binary  (~/.lqb/bin/liquibase)
  - Python package: liquibase-cli (this package)
"""

from __future__ import annotations

import io
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

LIQUIBASE_VERSION = "5.0.2"
LIQUIBASE_ZIP_URL = (
    f"https://github.com/liquibase/liquibase/releases/download/"
    f"v{LIQUIBASE_VERSION}/liquibase-{LIQUIBASE_VERSION}.zip"
)
LQB_BIN_DIR = Path.home() / ".lqb" / "bin"
LIQUIBASE_INSTALL_DIR = LQB_BIN_DIR / f"liquibase-{LIQUIBASE_VERSION}"

ON_WINDOWS = platform.system() == "Windows"
LIQUIBASE_BINARY = LIQUIBASE_INSTALL_DIR / ("liquibase.bat" if ON_WINDOWS else "liquibase")

JDBC_DRIVERS = {
    "postgresql": {
        "url": "https://jdbc.postgresql.org/download/postgresql-42.7.10.jar",
        "filename": "postgresql.jar",
        "detect": "jdbc:postgresql",
    },
    "mysql": {
        "url": "https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/9.3.0/mysql-connector-j-9.3.0.jar",
        "filename": "mysql-connector-j.jar",
        "detect": "jdbc:mysql",
    },
    "mariadb": {
        "url": "https://repo1.maven.org/maven2/org/mariadb/jdbc/mariadb-java-client/3.5.3/mariadb-java-client-3.5.3.jar",
        "filename": "mariadb-java-client.jar",
        "detect": "jdbc:mariadb",
    },
}


def _ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def _warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def _err(msg: str) -> None:
    print(f"  [ERR]  {msg}")


def _info(msg: str) -> None:
    print(f"  [ .. ] {msg}")


# ── checks ────────────────────────────────────────────────────────────────────

def check_python() -> bool:
    v = sys.version_info
    if v >= (3, 11):
        _ok(f"Python {v.major}.{v.minor}.{v.micro}")
        return True
    _err(f"Python 3.11+ required (found {v.major}.{v.minor}.{v.micro})")
    return False


def check_java() -> bool:
    java = shutil.which("java")
    if not java:
        _err("Java not found on PATH. Install JDK 11+ from https://adoptium.net")
        return False
    try:
        out = subprocess.check_output(
            ["java", "-version"], stderr=subprocess.STDOUT, text=True
        )
    except subprocess.CalledProcessError as e:
        out = e.output
    # version line: java version "17.0.12" or openjdk version "11.0.x"
    import re
    m = re.search(r'version "(\d+)', out)
    if m:
        major = int(m.group(1))
        if major >= 11:
            _ok(f"Java {out.splitlines()[0].strip()}")
            return True
        _err(f"Java 11+ required (found major={major})")
        return False
    _ok(f"Java found: {out.splitlines()[0].strip()}")
    return True


def check_liquibase() -> bool:
    # prefer our managed install
    if LIQUIBASE_BINARY.exists():
        _ok(f"Liquibase OSS {LIQUIBASE_VERSION} (managed) -> {LIQUIBASE_BINARY}")
        return True
    # fallback: something named 'liquibase' on PATH that isn't liquibase-secure
    lqb = shutil.which("liquibase")
    if lqb:
        try:
            out = subprocess.check_output(
                [lqb, "--version"], stderr=subprocess.STDOUT, text=True, timeout=15
            )
            if "liquibase-secure" in lqb.lower() or "Invalid license key" in out:
                _warn(f"Found {lqb} but it is the Pro edition (requires license key).")
                return False
            _ok(f"Liquibase on PATH: {lqb}")
            return True
        except Exception:
            pass
    return False


def check_pip_package() -> bool:
    try:
        import lqb  # noqa: F401
        _ok("liquibase-cli Python package installed")
        return True
    except ImportError:
        _warn("liquibase-cli not installed")
        return False


# ── installers ────────────────────────────────────────────────────────────────

def install_liquibase() -> bool:
    _info(f"Downloading Liquibase OSS {LIQUIBASE_VERSION} from GitHub ...")
    LQB_BIN_DIR.mkdir(parents=True, exist_ok=True)

    try:
        with urllib.request.urlopen(LIQUIBASE_ZIP_URL, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            data = bytearray()
            chunk = 1024 * 64
            downloaded = 0
            while True:
                block = resp.read(chunk)
                if not block:
                    break
                data.extend(block)
                downloaded += len(block)
                if total:
                    pct = downloaded * 100 // total
                    print(f"\r  [ .. ] {pct}% ({downloaded // 1024} KB)", end="", flush=True)
            print()
    except Exception as e:
        _err(f"Download failed: {e}")
        return False

    _info("Extracting ...")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            zf.extractall(LIQUIBASE_INSTALL_DIR)
    except Exception as e:
        _err(f"Extraction failed: {e}")
        return False

    # make binary executable on Unix
    if not ON_WINDOWS:
        LIQUIBASE_BINARY.chmod(0o755)

    _ok(f"Liquibase OSS installed -> {LIQUIBASE_INSTALL_DIR}")
    return True


def install_pip_package() -> bool:
    _info("Installing liquibase-cli Python package ...")
    project_dir = Path(__file__).parent
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", str(project_dir)],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        _ok("liquibase-cli installed")
        return True
    _err(f"pip install failed:\n{result.stderr}")
    return False


def install_jdbc_drivers(jdbc_url: str | None = None) -> None:
    lib_dir = LIQUIBASE_INSTALL_DIR / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    for name, info in JDBC_DRIVERS.items():
        dest = lib_dir / info["filename"]
        if dest.exists():
            _ok(f"JDBC driver already present: {info['filename']}")
            continue
        if jdbc_url and info["detect"] not in jdbc_url:
            continue
        _info(f"Downloading {name} JDBC driver ...")
        try:
            urllib.request.urlretrieve(info["url"], dest)
            _ok(f"{info['filename']} ({dest.stat().st_size // 1024} KB)")
        except Exception as e:
            _warn(f"Could not download {name} driver: {e}")


def write_lqb_env_config() -> None:
    """Write managed liquibase binary path to ~/.lqb/env so runner picks it up."""
    env_file = Path.home() / ".lqb" / "env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(f"LIQUIBASE_BINARY={LIQUIBASE_BINARY}\n")
    _ok(f"Binary path written to {env_file}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n=== lqb installer ===\n")
    print("Checking requirements ...\n")

    ok_python = check_python()
    ok_java = check_java()
    ok_lqb = check_liquibase()
    ok_pkg = check_pip_package()

    if not ok_python:
        print("\nFatal: upgrade Python and re-run.")
        sys.exit(1)

    if not ok_java:
        print("\nFatal: install Java 11+ and re-run.")
        sys.exit(1)

    fixes_needed: list[str] = []
    if not ok_lqb:
        fixes_needed.append("liquibase")
    if not ok_pkg:
        fixes_needed.append("pip-package")

    if not fixes_needed:
        print("\nAll requirements met. Run [lqb --help] to get started.")
        return

    print(f"\nInstalling: {', '.join(fixes_needed)} ...\n")

    if "liquibase" in fixes_needed:
        if not install_liquibase():
            print("\nLiquibase install failed. Check connection and retry.")
            sys.exit(1)
        install_jdbc_drivers()
        write_lqb_env_config()

    if "pip-package" in fixes_needed:
        if not install_pip_package():
            sys.exit(1)

    print("\n=== Done ===")
    print(f"  Liquibase OSS: {LIQUIBASE_BINARY}")
    print("  CLI:           lqb --help")

    if ON_WINDOWS:
        print(
            f"\n  NOTE: Add to PATH (optional):\n"
            f"    {LIQUIBASE_INSTALL_DIR}"
        )


if __name__ == "__main__":
    main()
