from __future__ import annotations

import questionary


def select(message: str, choices: list[str], default: str | None = None) -> str:
    return questionary.select(message, choices=choices, default=default).ask()


def text(message: str, default: str = "") -> str:
    return questionary.text(message, default=default).ask()


def password(message: str) -> str:
    return questionary.password(message).ask()


def confirm(message: str, default: bool = False) -> bool:
    return questionary.confirm(message, default=default).ask()


def confirm_protected(profile_name: str) -> bool:
    from lqb.ui.tables import console
    console.print(
        f"[bold red]!! Profile '{profile_name}' is PROTECTED.[/bold red] "
        "Type the profile name to confirm:"
    )
    val = questionary.text("Profile name:").ask()
    return val == profile_name
