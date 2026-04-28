from __future__ import annotations

SERVICE = "lqb"


def get_password(profile_name: str) -> str | None:
    try:
        import keyring
        return keyring.get_password(SERVICE, profile_name)
    except Exception:
        return None


def set_password(profile_name: str, password: str) -> None:
    try:
        import keyring
        keyring.set_password(SERVICE, profile_name, password)
    except Exception as e:
        from lqb.ui.tables import warn
        warn(f"Could not store password in keychain: {e}. Will prompt each time.")


def delete_password(profile_name: str) -> None:
    try:
        import keyring
        keyring.delete_password(SERVICE, profile_name)
    except Exception:
        pass
