"""First-run setup and wallet login."""

from base64 import b64encode
from urllib.parse import quote

from rich.console import Console
from rich.prompt import Prompt, Confirm

from APISDK.errors import DucoAPIError, DucoAPIHTTPError, DucoAPIOperationError
from APISDK.parsers import require_success
from core import runtime
from core.settings import Settings, SettingsError, load_settings, save_settings, validate_settings


def setup(console: Console) -> bool:
    """Prompt for account settings and save them after confirmation."""
    exists = runtime.SETTINGS_PATH.exists()
    if exists and not Confirm.ask("Replace existing settings?", default=False, console=console):
        return False
    console.print("Account setup. Leave password blank for read-only use.", style="duco.info")
    console.print("Saved passwords and mining keys are plain text in settings.toml.", style="duco.info")
    while True:
        username = Prompt.ask("DUCO username", console=console)
        password = Prompt.ask("Password (optional)", password=True, default="", console=console)
        mining_key = Prompt.ask("Mining key (optional)", password=True, default="", console=console)
        try:
            settings = validate_settings({
                "user": {"username": username, "password": password, "mining_key": mining_key},
            })
            break
        except SettingsError as exc:
            console.print(str(exc), style="duco.error")
    if not Confirm.ask("Save these settings?", default=True, console=console):
        return False
    save_settings(runtime.SETTINGS_PATH, settings, overwrite=exists)
    runtime.close_api()  # A new client must pick up any changed timeout.
    console.print("Settings saved. Run config check to verify the account.", style="duco.success")
    return True


def _auth_failure_reason(error: DucoAPIOperationError | DucoAPIHTTPError) -> str:
    """Explain a login failure using fixed text instead of the server's body."""
    message = error.message.strip().casefold()
    if error.status_code == 429 or "too many requests" in message or "rate limit" in message:
        return "The DUCO server is rate-limiting login attempts. Wait before trying again."
    if "captcha" in message:
        return "The DUCO server requires a CAPTCHA. Sign in through the official web wallet."
    if message == "user banned":
        return "The DUCO server says this account is banned."
    if message.startswith(("your ip", "you're using a proxy", "you're using a vpn")):
        return "The DUCO server rejected the connection based on its IP checks."
    if message == "invalid password":
        return (
            "The DUCO server returned 'Invalid password'. If you recently changed it, "
            "the server may still have the previous password cached."
        )
    if message in {"decoding error", "provide a password"}:
        return "The DUCO server could not read the password sent by the CLI."
    if message.startswith("this user doesn't exist") or message in {
        "incorrect username",
        "no user found",
    }:
        return "The DUCO login service did not recognise this username."
    if message.startswith("db err") or (error.status_code is not None and error.status_code >= 500):
        return "The DUCO login service reported an internal error."
    if error.status_code == 403:
        return "The DUCO server refused the login request (HTTP 403)."
    return "The DUCO server rejected the login without a recognised reason."


def verify_account(settings: Settings) -> None:
    """Check that the account exists, then verify its password when supplied.

    Read-only sessions can check the account balance without logging in.
    """
    api = runtime.get_api()
    try:
        api.get_balance(settings.user.username)
    except DucoAPIOperationError:
        raise SettingsError("DUCO account could not be found. Check user.username.") from None
    except DucoAPIError:
        raise SettingsError("Cannot reach the DUCO API to verify the account. Try again or use --read-only.") from None
    if settings.user.password and not runtime.READ_ONLY:
        endpoint = f"v2/auth/{quote(settings.user.username, safe='')}"
        encoded_password = b64encode(settings.user.password.encode("utf-8")).decode("ascii")
        try:
            payload = api.request_raw("GET", endpoint, params={"password": encoded_password})
            require_success(payload, endpoint="v2/auth")
        except (DucoAPIOperationError, DucoAPIHTTPError) as exc:
            raise SettingsError(f"Account authentication failed. {_auth_failure_reason(exc)}") from None
        except DucoAPIError:
            raise SettingsError("Cannot confirm account authentication. Try again or use --read-only.") from None


def prepare(console: Console) -> Settings | None:
    """Load settings, offering first-run setup when a terminal is available."""
    if not runtime.SETTINGS_PATH.exists():
        if not console.is_terminal:
            raise SettingsError("Settings missing. Run python run.py --setup in an interactive terminal.")
        if not setup(console):
            return None
    settings = load_settings(runtime.SETTINGS_PATH)
    if not runtime.READ_ONLY:
        verify_account(settings)
    return settings
