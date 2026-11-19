"""TOML settings and validation for DucoCLI."""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import tempfile
import tomllib


class SettingsError(ValueError):
    """Invalid or unreadable configuration that the CLI can report directly."""


def validate_username(value: object) -> str:
    """Trim the username and reject placeholders, spaces and URL delimiters."""
    if not isinstance(value, str) or not value.strip():
        raise SettingsError("Set username in the [user] section of settings.toml.")
    value = value.strip()
    if any(c.isspace() or not c.isprintable() or c in "/\\?#%" for c in value):
        raise SettingsError(
            "Username cannot contain whitespace, control characters or URL separators."
        )
    if value == "your_username":
        raise SettingsError("Replace the example username with your DUCO username.")
    return value


@dataclass(frozen=True)
class UserSettings:
    """Account name and optional password and mining key."""
    username: str
    password: str = field(default="", repr=False)
    mining_key: str = field(default="", repr=False)


@dataclass(frozen=True)
class Settings:
    """Account settings and the defaults for API calls and transaction history."""
    user: UserSettings
    timeout: float = 10.0
    transaction_limit: int = 10


def validate_settings(data: object) -> Settings:
    """Check the supported TOML tables and fill in omitted defaults."""
    if not isinstance(data, dict):
        raise SettingsError("Settings must be TOML tables.")
    allowed = {
        "user": {"username", "password", "mining_key"},
        "api": {"timeout"},
        "cli": {"transaction_limit"},
    }
    if set(data) - allowed.keys():
        raise SettingsError("Unknown settings section. Supported sections: user, api, cli.")
    for section, keys in allowed.items():
        table = data.get(section, {})
        if not isinstance(table, dict):
            raise SettingsError(f"[{section}] must be a TOML table.")
        if set(table) - keys:
            raise SettingsError(
                f"Unknown setting in [{section}]. Supported keys: {', '.join(sorted(keys))}."
            )
    user = data.get("user", {})
    username = validate_username(user.get("username"))
    for key in ("password", "mining_key"):
        value = user.get(key, "")
        if not isinstance(value, str) or any(not c.isprintable() for c in value):
            raise SettingsError(f"user.{key} must be a string without control characters.")
    timeout = data.get("api", {}).get("timeout", 10.0)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 1 <= timeout <= 120:
        raise SettingsError("api.timeout must be a finite number between 1 and 120 seconds.")
    limit = data.get("cli", {}).get("transaction_limit", 10)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise SettingsError("cli.transaction_limit must be an integer between 1 and 1000.")
    return Settings(
        UserSettings(username, user.get("password", ""), user.get("mining_key", "")),
        float(timeout),
        limit,
    )


def load_settings(path: str | Path) -> Settings:
    """Read and validate a settings file, accepting a UTF-8 BOM."""
    try:
        # Windows editors may prefix otherwise valid UTF-8 files with a BOM.
        data = tomllib.loads(Path(path).read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise SettingsError(
            "Create settings.toml with a [user] section and username first, "
            "or run python run.py --setup."
        ) from None
    except (tomllib.TOMLDecodeError, UnicodeError):
        raise SettingsError(
            "Cannot read settings.toml. Check TOML syntax and UTF-8 encoding; "
            "use --setup to reconfigure."
        ) from None
    except OSError:
        raise SettingsError("Cannot read settings.toml. Check the path and file permissions.") from None
    return validate_settings(data)


def save_settings(path: str | Path, settings: Settings, overwrite: bool = False) -> None:
    """Write settings atomically using a temporary file in the same directory.

    Replacing an existing file requires overwrite=True. Initial creation
    fails if another process has already saved the file.
    """
    path = Path(path)
    user = settings.user
    data = {
        "user": {
            "username": user.username,
            "password": user.password,
            "mining_key": user.mining_key,
        },
        "api": {"timeout": settings.timeout},
        "cli": {"transaction_limit": settings.transaction_limit},
    }
    validate_settings(data)
    content = "# DucoCLI settings. Password and mining key are stored as plain text.\n"
    for section, values in data.items():
        content += f"\n[{section}]\n"
        for key, value in values.items():
            content += f"{key} = {json.dumps(value, ensure_ascii=False)}\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".settings-",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temporary, path)
        else:
            # POSIX rename can overwrite another setup's file; a hard link can't.
            if os.name == "nt":
                os.rename(temporary, path)
            else:
                os.link(temporary, path)
    except FileExistsError:
        raise SettingsError(
            "Settings already exist; use --setup and confirm replacement."
        ) from None
    except OSError:
        raise SettingsError("Cannot save settings. Check the directory and permissions.") from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
