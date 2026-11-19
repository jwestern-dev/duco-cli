"""Inspect configuration without exposing passwords or mining keys."""

from core import runtime
from core.commands import CommandResult, command
from core.settings import load_settings
from core.startup import setup, verify_account
from core.ui import table_result


@command(name="config", description="Show masked settings, validate them, or run setup.",
         category="config", example="config [show|check|setup]")
def config(action: str = "show") -> CommandResult | None:
    """
    *config Show masked settings, verify the account, or run setup.*

    action str - Configuration action: show, check, or setup.
    """
    action = action.lower()
    if action == "setup":
        if not runtime.CONSOLE.is_terminal:
            raise ValueError("Run setup in an interactive terminal.")
        if setup(runtime.CONSOLE):
            runtime.CONSOLE.print("Restart DucoCLI to verify and use the new account settings.", style="duco.info")
            # The current prompt has not authenticated the newly saved account.
            runtime.READ_ONLY = True
            runtime.VERIFIED_USER = None
        return None
    if action not in ("show", "check"):
        raise ValueError("Usage: config [show|check|setup]")
    settings = load_settings(runtime.SETTINGS_PATH)
    if action == "check":
        verify_account(settings)
        message = ("Account exists. Password authentication skipped in read-only mode."
                   if runtime.READ_ONLY else "Settings and account checks passed.")
        return CommandResult(message=message)
    return table_result("Configuration", ["Setting", "Value"], [
        ("Settings file", runtime.SETTINGS_PATH), ("Username", settings.user.username),
        ("Password", "Configured (hidden)" if settings.user.password else "Not set"),
        ("Mining key", "Configured (hidden)" if settings.user.mining_key else "Not set"),
        ("API timeout (seconds)", settings.timeout), ("Transaction limit", settings.transaction_limit),
        ("Mode", "Read-only" if runtime.READ_ONLY else "Standard"),
    ])
