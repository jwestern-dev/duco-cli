"""Example command: add further command modules alongside this file."""

from core.commands import CommandResult, command


@command(name="echo", description="Repeat text", example='echo "Hello World!"',
         category="general", aliases=["say"])
def echo(*text: str) -> CommandResult:
    """
    *echo Join the supplied words and display them.*

    text str - Words to display.
    """
    return CommandResult(message=" ".join(text))
