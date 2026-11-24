"""First-run setup and wallet login."""

from base64 import b64encode
from time import sleep
from urllib.parse import quote

from rich.console import Console
from rich.prompt import Prompt, Confirm

from APISDK.errors import DucoAPIError, DucoAPIHTTPError, DucoAPIOperationError
from APISDK.parsers import require_success
from core import runtime
from core.debug import LOGGER
from core.ui import boot_status
from core.settings import Settings, SettingsError, load_settings, save_settings, validate_settings


def setup(console: Console) -> bool:
    """
    *setup Prompt for account settings and save them after confirmation.*

    console Console - Console receiving output or prompts.
    """
    exists = runtime.SETTINGS_PATH.exists()
    LOGGER.debug("Settings setup started: existing=%s", exists)
    if exists and not Confirm.ask("Replace existing settings?", default=False, console=console):
        return False
    console.print("Account setup. Leave password blank for read-only use.", style="duco.info")
    console.print("Saved passwords are plain text in settings.toml.", style="duco.info")
    while True:
        username = Prompt.ask("DUCO username", console=console)
        password = Prompt.ask("Password (optional)", password=True, default="", console=console)
        try:
            settings = validate_settings({
                "user": {"username": username, "password": password},
            })
            break
        except SettingsError as exc:
            console.print(str(exc), style="duco.error")
    if not Confirm.ask("Save these settings?", default=True, console=console):
        return False
    save_settings(runtime.SETTINGS_PATH, settings, overwrite=exists)
    LOGGER.debug("Settings saved")
    runtime.close_api()  # A new client must pick up any changed timeout.
    console.print("Settings saved. Run config check to verify the account.", style="duco.success")
    return True


def _auth_failure_reason(error: DucoAPIOperationError | DucoAPIHTTPError) -> str:
    """
    *_auth_failure_reason Explain a login failure using fixed text instead of the server's body.*

    error DucoAPIOperationError | DucoAPIHTTPError - Exception raised by the operation.
    """
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
            "The DUCO server returned 'Invalid password'. This can also happen when "
            "its login service encounters an internal error. Try again later or use --read-only."
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
    """
    *verify_account Check that the account exists, then verify its password when supplied.*

    settings Settings - Account settings and CLI preferences.

    Read-only sessions can check the account balance without logging in.
    """
    api = runtime.get_api()
    LOGGER.debug("Checking account balance")
    try:
        api.get_balance(settings.user.username)
    except DucoAPIOperationError:
        raise SettingsError("DUCO account could not be found. Check user.username.") from None
    except DucoAPIError:
        raise SettingsError("Cannot reach the DUCO API to verify the account. Try again or use --read-only.") from None
    if settings.user.password and not runtime.READ_ONLY:
        LOGGER.debug("Verifying account login")
        endpoint = f"v2/auth/{quote(settings.user.username, safe='')}"
        encoded_password = b64encode(settings.user.password.encode("utf-8")).decode("ascii")
        for attempt in (1, 2):
            try:
                payload = api.request_raw("GET", endpoint, params={"password": encoded_password})
                require_success(payload, endpoint="v2/auth")
                LOGGER.debug("Account login accepted on attempt %d", attempt)
                return
            except (DucoAPIOperationError, DucoAPIHTTPError) as exc:
                # The v2 route also uses this exact application error for internal failures.
                if (attempt == 1 and isinstance(exc, DucoAPIOperationError)
                        and exc.message.strip().casefold() == "invalid password"):
                    LOGGER.debug("Login returned 'Invalid password'; retrying once")
                    sleep(1)
                    continue
                reason = _auth_failure_reason(exc)
                LOGGER.debug("Login attempt %d failed: %s", attempt, reason)
                raise SettingsError(f"Account authentication failed. {reason}") from None
            except DucoAPIError:
                raise SettingsError("Cannot confirm account authentication. Try again or use --read-only.") from None


def prepare(console: Console) -> Settings | None:
    """
    *prepare Load settings, offering first-run setup when a terminal is available.*

    console Console - Console receiving output or prompts.
    """
    if not runtime.SETTINGS_PATH.exists():
        if not console.is_terminal:
            raise SettingsError("Settings missing. Run python run.py --setup in an interactive terminal.")
        if not setup(console):
            return None
    settings = load_settings(runtime.SETTINGS_PATH)
    boot_status(console, "OK", "Settings loaded")
    if runtime.READ_ONLY:
        boot_status(console, "SKIP", "Account login skipped (--read-only)")
    else:
        boot_status(console, "WAIT", "Checking account with the DUCO server…")
        verify_account(settings)
        if settings.user.password:
            boot_status(console, "OK", "Account verified")
        else:
            boot_status(console, "OK", "Account found · read-only access")
    LOGGER.debug("Settings loaded and startup checks complete")
    return settings
