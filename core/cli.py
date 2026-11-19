"""Command dispatch and the interactive DucoCLI prompt."""

import argparse
from collections.abc import Sequence
import inspect
from pathlib import Path
import shlex
from typing import Any

from rich.text import Text

from APISDK.errors import DucoAPIError, DucoAPIOperationError
from core import runtime
from core.commands import REGISTRY, CommandResult, load_commands
from core.runtime import CONSOLE, close_api
from core.settings import SettingsError, load_settings
from core.startup import prepare, setup
from core.theme import PRIMARY
from core.version import __version__

STARTUP_BANNER = rf"""
  ___                 ___ _    ___ 
 |   \ _  _ __ ___   / __| |  |_ _|
 | |) | || / _/ _ \ | (__| |__ | | 
 |___/ \_,_\__\___/  \___|____|___|
 
 - DucoCLI {__version__}
 - github.com/jwestern-dev/duco-cli
 """


def execute(line: str) -> Any:
    """Dispatch a shell line, including aliases and category-qualified names."""
    words = shlex.split(line)
    if not words:
        return None
    name = words.pop(0).lstrip("/")
    command = REGISTRY.get(name)
    category = name.lower()
    if command is None and category in REGISTRY.categories():
        if not words:
            return REGISTRY.get("help").invoke(name)
        name = words.pop(0).lstrip("/")
        command = REGISTRY.get(name)
        if command is None or command.category != category:
            return CommandResult(ok=False, message=f"Unknown command: {category} {name}")
    if command is None:
        return CommandResult(ok=False, message=f"Unknown command: {name}. Use help.")
    try:
        inspect.signature(command.callback).bind(*words)
    except TypeError:
        return CommandResult(ok=False, message=f"Usage: {command.example or command.name}")
    return command.invoke(*words)


def main(argv: Sequence[str] | None = None) -> int:
    """Handle command-line options or start the interactive prompt."""
    parser = argparse.ArgumentParser(description="DucoCLI: Duino-Coin wallet and network terminal.")
    parser.add_argument("--version", action="version", version=f"DucoCLI {__version__}")
    parser.add_argument("--settings", type=Path, help="Use a different TOML settings file")
    parser.add_argument("--setup", action="store_true", help="Create or replace settings interactively")
    parser.add_argument("--check-config", action="store_true", help="Validate settings locally and exit")
    parser.add_argument("--read-only", action="store_true", help="Skip startup login and disable send/buy")
    args = parser.parse_args(argv)
    if args.settings:
        runtime.SETTINGS_PATH = args.settings.resolve()
    runtime.READ_ONLY = args.read_only
    try:
        if args.check_config:
            load_settings(runtime.SETTINGS_PATH)
            CONSOLE.print("Settings are valid. No network requests were made.", style="duco.success")
            return 0
        if args.setup:
            if not CONSOLE.is_terminal:
                raise SettingsError("Run --setup in an interactive terminal.")
            return 0 if setup(CONSOLE) else 1
        settings = prepare(CONSOLE)
        if settings is None:
            return 0
        runtime.READ_ONLY = args.read_only or not settings.user.password
        runtime.VERIFIED_USER = None if runtime.READ_ONLY else settings.user
        load_commands()
        mode = "read-only" if runtime.READ_ONLY else "account verified"
        CONSOLE.print(STARTUP_BANNER, style="duco.title")
        CONSOLE.print(f"Startup complete. {mode}. Type 'help' for commands.", style="duco.success")
        while True:
            try:
                line = CONSOLE.input(
                    Text(f"{settings.user.username}@ducoCLI:-$ ", style=f"bold {PRIMARY}")
                )
            except (EOFError, KeyboardInterrupt):
                CONSOLE.print()
                return 0
            try:
                result = execute(line)
                if isinstance(result, CommandResult):
                    if result.data is not None:
                        CONSOLE.print(result.data)
                    else:
                        CONSOLE.print(str(result), style="duco.success" if result.ok else "duco.error")
                elif result is not None:
                    CONSOLE.print(result)
            except DucoAPIError as exc:
                if isinstance(exc, DucoAPIOperationError):
                    CONSOLE.print(str(exc), style="duco.error")
                else:
                    CONSOLE.print("API request failed. Please try again later.", style="duco.error")
            except (ValueError, OSError) as exc:
                CONSOLE.print(f"Error: {exc}", style="duco.error")
            except (EOFError, KeyboardInterrupt):
                CONSOLE.print("Command cancelled.", style="duco.warning")
            except Exception:
                # SDK tracebacks can include URLs containing credentials.
                CONSOLE.print(
                    "This command failed unexpectedly. Check settings, then try again. "
                    "If it persists, report the command name and application version.",
                    style="duco.error",
                )
    except SettingsError as exc:
        CONSOLE.print(f"Settings error: {exc}", style="duco.error")
        return 2
    except (EOFError, KeyboardInterrupt):
        CONSOLE.print("Startup cancelled.", style="duco.warning")
        return 130
    except (ImportError, ValueError):
        CONSOLE.print("Command startup failed. Check the installation and command modules.", style="duco.error")
        return 1
    finally:
        runtime.VERIFIED_USER = None
        close_api()
