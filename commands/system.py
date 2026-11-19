"""System commands and registry-driven help."""

from core.commands import REGISTRY, CommandResult, command
from core.runtime import CONSOLE
from core.ui import table_result


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
        return table_result("Command categories", ["Category", "Commands", "Description"],
                            rows, "\n".join(f"{row[0]} - {row[1]} - {row[2]}" for row in rows))
    if category not in groups:
        cmd = REGISTRY.get(category)
        if cmd is None or name:
            return CommandResult(ok=False, message=f"Unknown category or command: {category}")
        category, name = cmd.category, cmd.name
    if name:
        cmd = REGISTRY.get(name)
        if cmd is None or cmd.category != category:
            return CommandResult(ok=False, message=f"Unknown command: {category} {name}")
        return table_result(f"Help for {category} - {cmd.name}", ["Field", "Value"],
                            [("Description", cmd.description), ("Example", cmd.example or cmd.name),
                             ("Aliases", ", ".join(cmd.aliases) or "None")], cmd.description)
    rows = [(cmd.name, ", ".join(cmd.aliases), cmd.description) for cmd in groups[category]]
    return table_result(REGISTRY.get_category_description(category) or category,
                        ["Command", "Aliases", "Description"], rows,
                        "\n".join(f"{row[0]} - {row[2]}" for row in rows))


@command(name="quit", description="Close the application.", category="system",
         aliases=["close", "leave", "shutdown", "exit"])
def quit_command() -> None:
    """
    *quit_command Exit the application with a successful status.*
    """
    raise SystemExit(0)


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
