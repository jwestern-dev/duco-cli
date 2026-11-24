"""System commands and registry-driven help."""

from collections.abc import Sequence

from core.commands import REGISTRY, CommandResult, command
from core.runtime import CONSOLE
from core.ui import table_result
from core.runtime import RestartSession
from core.theme import ACCENT


def _help_table(title: str, columns: Sequence[str], rows: Sequence[Sequence[str]],
                message: str, *, hint: str = "") -> CommandResult:
    """
    *_help_table Build a help table with command names, aliases and examples highlighted.*

    title str - Title above the table.
    columns Sequence[str] - Column headings in display order.
    rows Sequence[Sequence[str]] - Values for each table row.
    message str - Message for the caller.
    hint str - Optional guidance below the table.
    """
    result = table_result(title, columns, rows, message, hint=hint)
    table = result.data
    table.header_style = f"bold {ACCENT}"
    table.columns[0].style = f"bold {ACCENT}"
    if "Aliases" in columns:
        table.columns[columns.index("Aliases")].style = "cyan"
    if columns[0] == "Field":
        for row, (field, _) in zip(table.rows, rows):
            if field in {"Example", "Aliases"}:
                row.style = "cyan"
    table.caption_style = "cyan"
    return result


@command(name="help", description="List all commands, or relevant command / category info.",
         category="system", example="help [category] [command]")
def help_command(category: str = "", name: str = "") -> CommandResult:
    """
    *help_command Show the command index, a category, or an individual command.*

    category str - Category or command name.
    name str - Command to describe within the selected category.
    """
    groups = REGISTRY.categories()
    category = category.lower().lstrip("/")
    if not category:
        rows = [
            (key, f"{len(commands)} command{'s' if len(commands) != 1 else ''}",
             REGISTRY.get_category_description(key))
            for key, commands in groups.items()
        ]
        return _help_table("Command categories", ["Category", "Commands", "Description"],
                            rows, "\n".join(f"{row[0]} - {row[1]} - {row[2]}" for row in rows),
                            hint="Try help wallet to list wallet commands.")
    if category not in groups:
        cmd = REGISTRY.get(category)
        if cmd is None or name:
            return CommandResult(ok=False, message=f"Unknown category or command: {category}")
        category, name = cmd.category, cmd.name
    if name:
        cmd = REGISTRY.get(name)
        if cmd is None or cmd.category != category:
            return CommandResult(ok=False, message=f"Unknown command: {category} {name}")
        return _help_table(f"Help for {category} - {cmd.name}", ["Field", "Value"],
                            [("Description", cmd.description), ("Example", cmd.example or cmd.name),
                             ("Aliases", ", ".join(cmd.aliases) or "None")], cmd.description)
    rows = [(cmd.name, ", ".join(cmd.aliases), cmd.description) for cmd in groups[category]]
    return _help_table(REGISTRY.get_category_description(category) or category,
                        ["Command", "Aliases", "Description"], rows,
                        "\n".join(f"{row[0]} - {row[2]}" for row in rows),
                        hint=f"Try help {category} {rows[0][0]} for usage." if rows else "")


@command(name="quit", description="Close the application.", category="system",
         aliases=["close", "leave", "shutdown", "exit"])
def quit_command() -> None:
    """
    *quit_command Exit the application with a successful status.*
    """
    raise SystemExit(0)


@command(name="restart", description="Reload settings and restart the interactive session.", category="system")
def restart() -> None:
    """
    *restart Request a fresh interactive session with the current startup options.*
    """
    raise RestartSession()


@command(name="clear", description="Clear the terminal.", category="system", aliases=["cls"])
def clear_command() -> None:
    """
    *clear_command Clear the terminal.*
    """
    CONSOLE.clear()


@command(name="version", description="Show application and Python versions.", category="system", example="version")
def version_command() -> CommandResult:
    """
    *version_command Show the application and Python versions.*
    """
    import platform
    from core.version import __version__
    return table_result("Version", ["Component", "Version"],
                        [("DucoCLI", __version__), ("Python", platform.python_version())])
