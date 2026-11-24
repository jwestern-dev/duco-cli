"""Console, API client and account state for the current CLI session."""

from dataclasses import asdict
from pathlib import Path

from rich.console import Console

from APISDK import DucoAPI, DucoAPIConfig
from core.settings import UserSettings, load_settings, validate_username
from core.theme import THEME

CONSOLE = Console(theme=THEME, emoji=False, markup=False, highlight=False)
SETTINGS_PATH = Path(__file__).resolve().parents[1] / "settings.toml"
_API: DucoAPI | None = None
READ_ONLY = False
VERIFIED_USER: UserSettings | None = None
RIG_IDENTIFIERS: tuple[str, ...] = ()


class RestartSession(Exception):
    """
    *RestartSession Return to startup after disposing of the current session.*

    args object - Optional exception arguments. The shell raises this signal without arguments.
    """


def get_api() -> DucoAPI:
    """
    *get_api Create the shared API client on the first request.*
    """
    global _API
    if _API is None:
        timeout = load_settings(SETTINGS_PATH).timeout if SETTINGS_PATH.exists() else 10.0
        _API = DucoAPI(config=DucoAPIConfig(timeout=timeout))
    return _API


def close_api() -> None:
    """
    *close_api Dispose of the shared client so a later call can open a new session.*
    """
    global _API
    if _API is not None:
        api, _API = _API, None
        api.close()


def user_settings() -> dict[str, str]:
    """
    *user_settings Read the current account and credentials from disk.*
    """
    return asdict(load_settings(SETTINGS_PATH).user)


def configured_username(username: str | None = None) -> str:
    """
    *configured_username Validate the supplied username or fall back to the configured account.*

    username str | None - DUCO account name.
    """
    value = username if username is not None else user_settings().get("username")
    return validate_username(value)


def transaction_limit() -> int:
    """
    *transaction_limit Read the configured limit for transaction history.*
    """
    return load_settings(SETTINGS_PATH).transaction_limit if SETTINGS_PATH.exists() else 10


def require_writes() -> UserSettings:
    """
    *require_writes Return the startup credentials if this session can spend DUCO.*
    """
    if READ_ONLY:
        raise ValueError("Read-only mode: restart without --read-only to send DUCO or buy items.")
    if VERIFIED_USER is None:
        raise ValueError("Start DucoCLI and verify your account before sending DUCO or buying items.")
    return VERIFIED_USER
