"""Command dispatch and the interactive DucoCLI prompt."""

import argparse
from collections.abc import Sequence
from contextlib import nullcontext, redirect_stdout
import inspect
import json
from pathlib import Path
import shlex
import sys
from time import perf_counter
from typing import Any

from prompt_toolkit import PromptSession
from rich.text import Text

from APISDK.errors import DucoAPIError, DucoAPIOperationError
from core import runtime
from core.boot_checks import check_endpoints
from core.debug import DebugLogOpenError, debug_session, log_failure, LOGGER
from core.commands import REGISTRY, CommandResult, load_commands
from core.completion import CommandCompleter, EDITING_KEYS
from core.runtime import CONSOLE, close_api
from core.settings import SettingsError, load_settings
from core.shell import parse_chain
from core.startup import prepare, setup, verify_account
from core.theme import PRIMARY
from core.ui import STARTUP_BANNER, boot_status, session_panel
from core.version import __version__


def execute(line: str | Sequence[str], *, one_shot: bool = False) -> Any:
    """
    *execute Dispatch a shell line, including aliases and category-qualified names.*

    line str | Sequence[str] - Command text or tokens to dispatch.
    one_shot bool - Whether the caller will exit after this command.
    """
    words = shlex.split(line) if isinstance(line, str) else list(line)
    if not words:
        return None
    name = words.pop(0).lstrip("/")
    command = REGISTRY.get(name)
    category = name.lower()
    qualified = REGISTRY.get(words[0].lstrip("/")) if words else None
    if category in REGISTRY.categories() and (command is None or (qualified and qualified.category == category)):
        if not words:
            LOGGER.debug("Category help: %s", category)
            return REGISTRY.get("help").invoke(name)
        name = words.pop(0).lstrip("/")
        command = REGISTRY.get(name)
        if command is None or command.category != category:
            LOGGER.debug("Unknown command in category %s", category)
            return CommandResult(ok=False, message=f"Unknown command: {category} {name}")
    if command is None:
        LOGGER.debug("Unknown command")
        return CommandResult(ok=False, message=f"Unknown command: {name}. Use help.")
    LOGGER.debug("Command: %s.%s arguments=%d", command.category, command.name, len(words))
    try:
        inspect.signature(command.callback).bind(*words)
    except TypeError:
        LOGGER.debug("Command rejected: incorrect argument count")
        return CommandResult(ok=False, message=f"Usage: {command.example or command.name}")
    started = perf_counter()
    if one_shot and command.requires_verified_user and not runtime.READ_ONLY:
        settings = load_settings(runtime.SETTINGS_PATH)
        runtime.READ_ONLY = not settings.user.password
        if not runtime.READ_ONLY:
            verify_account(settings)
            runtime.VERIFIED_USER = settings.user
    result = command.invoke(*words)
    LOGGER.debug("Command completed: %s ok=%s elapsed_ms=%.1f", command.name,
                 result.ok if isinstance(result, CommandResult) else True,
                 (perf_counter() - started) * 1000)
    return result


def command_result(line: str | Sequence[str], *, one_shot: bool = False) -> CommandResult:
    """
    *command_result Turn command output, validation errors and one-shot exits into a command result.*

    line str | Sequence[str] - Command text or tokens to dispatch.
    one_shot bool - Whether the caller will exit after this command.
    """
    try:
        result = execute(line, one_shot=one_shot)
        return result if isinstance(result, CommandResult) else CommandResult(data=result)
    except runtime.RestartSession:
        if not one_shot:
            raise
        message = "Use restart inside the interactive shell."
    except SystemExit as exc:
        if not one_shot:
            raise
        return CommandResult(ok=not exc.code)
    except DucoAPIError as exc:
        log_failure("Command API request", exc)
        message = str(exc) if isinstance(exc, DucoAPIOperationError) else "API request failed. Please try again later."
    except (ValueError, OSError) as exc:
        log_failure("Command", exc)
        message = f"Error: {exc}"
    except (EOFError, KeyboardInterrupt):
        LOGGER.debug("Command cancelled")
        if not one_shot:
            raise
        message = "Command cancelled."
    except Exception as exc:
        log_failure("Command", exc)
        message = "This command failed unexpectedly. Check settings, then try again."
    return CommandResult(ok=False, message=message)


def show_result(result: CommandResult, json_output: bool = False) -> int:
    """
    *show_result Render a result and return the corresponding process exit code.*

    result CommandResult - Command outcome to render.
    json_output bool - Whether to emit machine-readable JSON.
    """
    if json_output:
        data = result.records if result.records is not None else result.data
        print(json.dumps({"ok": result.ok, "message": result.message, "data": data}, default=str))
    elif result.data is not None:
        CONSOLE.print(result.data)
    elif result.message:
        CONSOLE.print(result.message, style="duco.success" if result.ok else "duco.error")
    return 0 if result.ok else 1


def run_shell_line(line: str) -> None:
    """
    *run_shell_line Execute a command chain from left to right using each preceding result.*

    line str - Shell input before quote and escape processing.
    """
    try:
        chain = parse_chain(line)
    except ValueError as exc:
        show_result(CommandResult(False, f"Syntax error: {exc}"))
        return
    ok = True
    try:
        for operator, words in chain:
            if (operator == "&&" and not ok) or (operator == "||" and ok):
                continue
            result = command_result(words)
            show_result(result)
            ok = result.ok
    except (EOFError, KeyboardInterrupt):
        CONSOLE.print("Command cancelled.", style="duco.warning")


def main(argv: Sequence[str] | None = None) -> int:
    """
    *main Handle command-line options or start the interactive prompt.*

    argv Sequence[str] | None - Command-line arguments after the executable name.
    """
    argv = sys.argv[1:] if argv is None else argv
    options = argv[:argv.index("--")] if "--" in argv else argv
    try:
        with debug_session("--debug" in options):
            try:
                while True:
                    try:
                        status = _run(argv)
                        break
                    except runtime.RestartSession:
                        LOGGER.debug("Restarting interactive session")
            except SystemExit as exc:
                LOGGER.debug("Exit status=%s", exc.code if isinstance(exc.code, int) else "unspecified")
                raise
            LOGGER.debug("Exit status=%d", status)
            return status
    except DebugLogOpenError:
        return show_result(CommandResult(False, "Cannot open debug.log for writing in the current directory."),
                           "--json" in options)


def _run(argv: Sequence[str]) -> int:
    """
    *_run Handle startup flags and either dispatch a command or open the shell.*

    argv Sequence[str] - Command-line arguments after the executable name.
    """
    parser = argparse.ArgumentParser(description="DucoCLI: Duino-Coin wallet and network terminal.", exit_on_error=False,
                                     usage="%(prog)s [options] [command [arguments ...]]", allow_abbrev=False)
    parser.add_argument("--debug", action="store_true", help="Append diagnostics to debug.log in the working directory")
    parser.add_argument("--version", action="store_true", help="Print the application version")
    parser.add_argument("--json", action="store_true", help="Write a single JSON result for a command")
    parser.add_argument("--settings", type=Path, help="Use a different TOML settings file")
    parser.add_argument("--setup", action="store_true", help="Create or replace settings interactively")
    parser.add_argument("--check-config", action="store_true", help="Validate settings locally and exit")
    parser.add_argument("--read-only", action="store_true", help="Skip startup login and disable send/buy")
    try:
        args, words = parser.parse_known_args(argv)
    except argparse.ArgumentError as exc:
        show_result(CommandResult(False, str(exc)), "--json" in argv)
        return 2
    if "--" in words:
        words.remove("--")
    LOGGER.debug("Options: setup=%s check_config=%s read_only=%s custom_settings=%s",
                 args.setup, args.check_config, args.read_only, args.settings is not None)
    if args.settings:
        runtime.SETTINGS_PATH = args.settings.resolve()
    runtime.READ_ONLY = args.read_only
    try:
        if sum(map(bool, (args.version, args.check_config, args.setup, words))) > 1:
            return show_result(CommandResult(False, "Choose one command or startup action."), args.json)
        if args.version:
            return show_result(CommandResult(message=f"DucoCLI {__version__}"), args.json)
        if words:
            load_commands()
            # Keep confirmation panels and prompts off machine-readable stdout.
            with redirect_stdout(sys.stderr) if args.json else nullcontext():
                result = command_result(words, one_shot=True)
            return show_result(result, args.json)
        if args.check_config:
            load_settings(runtime.SETTINGS_PATH)
            LOGGER.debug("Settings validation passed")
            return show_result(CommandResult(message="Settings are valid. No network requests were made."), args.json)
        if args.json:
            return show_result(CommandResult(False, "--json requires a command, --version, or --check-config."), True)
        if args.setup:
            if not CONSOLE.is_terminal:
                raise SettingsError("Run --setup in an interactive terminal.")
            return 0 if setup(CONSOLE) else 1
        boot_status(CONSOLE, "WAIT", "Loading settings…")
        settings = prepare(CONSOLE)
        if settings is None:
            return 0
        runtime.READ_ONLY = args.read_only or not settings.user.password
        runtime.VERIFIED_USER = None if runtime.READ_ONLY else settings.user
        load_commands()
        boot_status(CONSOLE, "OK", f"Loaded {len(REGISTRY.all())} commands")
        LOGGER.debug("Shell ready: commands=%d read_only=%s", len(REGISTRY.all()), runtime.READ_ONLY)
        mode = "read-only" if runtime.READ_ONLY else "account verified"
        interactive = CONSOLE.is_terminal and sys.stdin.isatty()
        notices = []
        if interactive:
            notices = check_endpoints(CONSOLE, settings)
            CONSOLE.clear()
        CONSOLE.print(Text(STARTUP_BANNER, style="duco.title", no_wrap=True, overflow="crop"))
        CONSOLE.print(session_panel(settings.user.username, mode, __version__, interactive))
        for notice in notices:
            boot_status(CONSOLE, "WARN", notice)
        prompt_parts = [
            ("bold", settings.user.username),
            (f"bold {PRIMARY}", " > "),
        ]
        prompt = Text.assemble(*((value, style) for style, value in prompt_parts))
        session = None
        if interactive:
            session = PromptSession(prompt_parts, completer=CommandCompleter(),
                                    complete_while_typing=True, key_bindings=EDITING_KEYS)
        while True:
            try:
                line = session.prompt() if session else CONSOLE.input(prompt)
            except (EOFError, KeyboardInterrupt):
                LOGGER.debug("Prompt closed")
                CONSOLE.print()
                return 0
            run_shell_line(line)
    except SettingsError as exc:
        log_failure("Settings", exc)
        if not (words or args.json or args.setup or args.check_config):
            boot_status(CONSOLE, "FAIL", f"Settings error: {exc}")
        else:
            show_result(CommandResult(False, f"Settings error: {exc}"), args.json)
        return 2
    except (EOFError, KeyboardInterrupt):
        LOGGER.debug("Startup cancelled")
        show_result(CommandResult(False, "Startup cancelled."), args.json)
        return 130
    except (ImportError, ValueError) as exc:
        log_failure("Startup", exc)
        show_result(CommandResult(False, "Command startup failed. Check the installation and command modules."), args.json)
        return 1
    finally:
        runtime.VERIFIED_USER = None
        runtime.RIG_IDENTIFIERS = ()
        close_api()
