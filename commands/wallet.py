"""Wallet queries and explicitly confirmed transfers."""

import argparse
from dataclasses import fields
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from rich.panel import Panel
from rich.prompt import Confirm
from rich.text import Text

from APISDK import DucoAPIRequestConfig, UnixTimestamp
from APISDK.errors import DucoAPIError, DucoAPIHTTPError, DucoAPIOperationError
from APISDK.parsers import require_success
from core.commands import CommandResult, command
from core.runtime import CONSOLE, configured_username, get_api, require_writes, transaction_limit
from core.settings import validate_username
from core.theme import ACCENT
from core.ui import format_decimal, plain_html, table_result


class FilterParser(argparse.ArgumentParser):
    """
    *FilterParser Report transaction filter errors through the command result handler.*

    prog str | None - Program name shown in usage text.
    usage str | None - Override for the generated usage line.
    description str | None - Text displayed before the argument descriptions.
    epilog str | None - Text displayed after the argument descriptions.
    parents Sequence[ArgumentParser] - Parsers supplying shared arguments.
    formatter_class type[HelpFormatter] - Formatter for usage and help.
    prefix_chars str - Characters that introduce optional arguments.
    fromfile_prefix_chars str | None - Prefixes for files containing arguments.
    argument_default object - Default used for arguments without an explicit default.
    conflict_handler str - Policy for conflicting option names.
    add_help bool - Whether to register the standard help option.
    allow_abbrev bool - Whether unambiguous long-option prefixes are accepted.
    exit_on_error bool - Standard argparse policy for parse errors.

    Construction follows argparse.ArgumentParser on the running Python version.
    """

    def error(self, message):
        """
        *error Raise a command error instead of exiting the shell on invalid filters.*

        message str - Message for the caller.
        """
        raise ValueError(f"Transaction filters: {message}")


TRANSACTION_FILTERS = FilterParser(prog="transactions", add_help=False, allow_abbrev=False)
TRANSACTION_FILTERS.add_argument("username", nargs="?")
DIRECTION_OPTIONS = TRANSACTION_FILTERS.add_mutually_exclusive_group()
DIRECTION_OPTIONS.add_argument("--incoming", action="store_true")
DIRECTION_OPTIONS.add_argument("--outgoing", action="store_true")
TRANSACTION_FILTERS.add_argument("--from", dest="sender", type=validate_username)
TRANSACTION_FILTERS.add_argument("--to", dest="recipient", type=validate_username)
TRANSACTION_FILTERS.add_argument("--limit", type=int)


def available_filters(arguments: list[str]) -> set[str]:
    """
    *available_filters Suggest unused filter flags that are valid after the current arguments.*

    arguments list[str] - Transaction history arguments supplied so far.
    """
    takes_value = {"--from", "--to", "--limit"}
    if arguments and arguments[-1] in takes_value:
        return set()
    available = takes_value.difference(arguments)
    if not {"--incoming", "--outgoing"}.intersection(arguments):
        available.update(("--incoming", "--outgoing"))
    return available


@command(name="transactions", description="List user transactions.", category="wallet",
         example="transactions [username] [--incoming|--outgoing] [--from USER] [--to USER] [--limit N]",
         aliases=["gettransactions", "listtransactions"],
         completers={"options": available_filters})
def transactions(*arguments: str, username: str | None = None) -> CommandResult:
    """
    *transactions List recent transactions for the requested account.*

    arguments str - Transaction history arguments supplied so far.
    username str | None - Account to look up, defaulting to the configured username.
    """
    options = TRANSACTION_FILTERS.parse_args(arguments)
    user = configured_username(options.username or username)
    limit = transaction_limit() if options.limit is None else options.limit
    if not 1 <= limit <= 1000:
        raise ValueError("--limit must be between 1 and 1000.")
    items = get_api().get_user_transactions(user, limit=limit)
    matches = [
        entry for entry in items
        if (not options.incoming or entry.recipient.casefold() == user.casefold())
        and (not options.outgoing or entry.sender.casefold() == user.casefold())
        and (not options.sender or entry.sender.casefold() == options.sender.casefold())
        and (not options.recipient or entry.recipient.casefold() == options.recipient.casefold())
    ]
    counts = f"{len(matches)} matched, {len(items)} searched"
    if len(items) < limit:
        counts += f", {limit} requested"
    return table_result(
        f"Recent transactions for {user} ({counts})",
        ["ID", "Date (UTC)", "Sender", "Recipient", "DUCO", "Memo", "Hash"],
        [(entry.id, entry.datetime, entry.sender, entry.recipient, entry.amount, entry.memo, entry.hash)
         for entry in matches],
    )


@command(name="balance", description="Get user balance.", category="wallet",
         example="balance [username]", aliases=["bal"])
def balance(username: str | None = None) -> CommandResult:
    """
    *balance Display the account balance and staked amount.*

    username str | None - Account to look up, defaulting to the configured username.
    """
    user = configured_username(username)
    result = get_api().get_balance(user)
    return table_result(f"Wallet balance for {result.username}", ["Field", "Value"],
                        [("Balance (DUCO)", result.balance), ("Staked (DUCO)", result.stake_amount),
                         ("Updated (UTC)", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))])


@command(name="send", description="Send DUCO to another user.", category="wallet",
         example='send user123 10.5 "Happy Birthday!"', requires_verified_user=True)
def send(username: str, amount: str, memo: str = "None") -> CommandResult:
    """
    *send Confirm and submit a transfer from the verified session account.*

    username str - Recipient account name.
    amount str - Exact DUCO amount as entered at the prompt.
    memo str - Text attached to the transfer.
    """
    user = require_writes()
    # Parse the original text directly to Decimal, avoiding float rounding.
    try:
        value = Decimal(amount)
    except (InvalidOperation, ValueError):
        raise ValueError("Amount must be a positive finite number.") from None
    if not value.is_finite() or value <= 0:
        raise ValueError("Amount must be a positive finite number.")
    # Bound fixed-point expansion before allocating the preview or request string.
    integer_digits = max(1, value.adjusted() + 1)
    fraction_digits = max(0, -value.as_tuple().exponent)
    if integer_digits + fraction_digits > 128:
        raise ValueError("Amount must fit within 128 digits in decimal notation.")
    recipient = configured_username(username)
    amount_text = format(value, "f")
    summary = Text(
        f"From: {user.username}\n"
        f"Recipient: {recipient}\n"
        f"Amount: {amount_text} DUCO\n"
        f"Memo: {memo}\n\n"
        "Check the recipient and amount carefully before confirming."
    )
    CONSOLE.print(
        Panel(summary, title=Text("Confirm transfer", style=f"bold {ACCENT}"), border_style=ACCENT)
    )
    if not Confirm.ask("Send this transfer?", default=False, console=CONSOLE):
        return CommandResult(ok=False, message="Transfer cancelled.")
    try:
        payload = get_api().request_raw(
            "GET",
            "transaction/",
            params={
                "username": user.username,
                "password": user.password,
                "recipient": recipient,
                "amount": amount_text,
                "memo": memo,
            },
            config=DucoAPIRequestConfig(allow_redirects=False),
        )
        require_success(payload, endpoint="transaction")
    except DucoAPIOperationError:
        return CommandResult(
            ok=False,
            message="The API rejected the transfer. Check the account, recipient and balance.",
        )
    except DucoAPIHTTPError as exc:
        return CommandResult(
            ok=False,
            message=(
                f"Could not confirm the transfer result (HTTP {exc.status_code}). "
                "Check transactions before sending again."
            ),
        )
    except (DucoAPIError, KeyboardInterrupt):
        # Transport exceptions can contain credential-bearing request URLs.
        return CommandResult(
            ok=False,
            message="Could not confirm the transfer result. Check transactions before sending again.",
        )
    return CommandResult(message="Transfer confirmed by the API.", data=None)


@command(name="profile", description="Show account details and verification status.",
         category="wallet", example="profile [username]")
def profile(username: str | None = None) -> CommandResult:
    """
    *profile Show account details and verification status.*

    username str | None - Account to look up, defaulting to the configured username.
    """
    account = get_api().get_balance(configured_username(username))

    def timestamp(value: UnixTimestamp) -> str:
        """
        *timestamp Format a supplied Unix timestamp for the profile table.*

        value UnixTimestamp - Timestamp provided by the account response.
        """
        if not value:
            return "Not set"
        try:
            return datetime.fromtimestamp(value, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        except (ValueError, OverflowError, OSError):
            return str(value)

    return table_result(f"Profile for {account.username}", ["Field", "Value"], [
        ("Username", account.username), ("Created (UTC)", account.created),
        ("Last login", timestamp(account.last_login)), ("Balance (DUCO)", account.balance),
        ("Staked (DUCO)", account.stake_amount), ("Stake date", timestamp(account.stake_date)),
        ("Verified", account.verified), ("Verified by", account.verified_by),
        ("Verified date", timestamp(account.verified_date)), ("Trust score", account.trust_score),
        ("Warnings", account.warnings), ("Miner limit", account.max_miners),
    ])


@command(name="transaction", description="Look up a transaction by ID or hash.", category="wallet",
         example="transaction <id-or-hash> (use hash:<hash> for a numeric hash)")
def transaction(identifier: str) -> CommandResult:
    """
    *transaction Look up a transaction by its numeric ID or hash.*

    identifier str - Transaction ID or hash, optionally prefixed with id: or hash:.
    """
    kind, separator, value = identifier.partition(":")
    if separator:
        if kind.lower() not in ("id", "hash") or not value:
            raise ValueError("Use a transaction ID, hash, id:<id>, or hash:<hash>.")
        by_id = kind.lower() == "id"
    else:
        value = identifier
        by_id = value.isascii() and value.isdigit()
    if by_id:
        if not value.isascii() or not value.isdigit() or int(value) <= 0:
            raise ValueError("Transaction ID must be a positive integer.")
        item = get_api().get_transaction_by_id(int(value))
    else:
        item = get_api().get_transaction(value)
    return table_result(f"Transaction {item.id}", ["Field", "Value"], [
        ("ID", item.id), ("Hash", item.hash), ("Date (UTC)", item.datetime),
        ("Sender", item.sender), ("Recipient", item.recipient),
        ("Amount (DUCO)", item.amount), ("Memo", item.memo),
    ])


@command(name="achievements", description="Show unlocked achievement names, requirements and rewards.",
         category="wallet", example="achievements [username]")
def achievements(username: str | None = None) -> CommandResult:
    """
    *achievements List the unlocked achievements and their catalogue details.*

    username str | None - Account to look up, defaulting to the configured username.
    """
    user = configured_username(username)
    items = get_api().get_user_v3(user).achievements
    catalogue = {}
    note = ""
    if items:
        try:
            response = require_success(get_api().request_raw("GET", "achievements"), endpoint="achievements")
            if not isinstance(response.result, dict):
                raise ValueError("Invalid achievement catalogue")
            catalogue = response.result
        except (DucoAPIError, ValueError):
            note = "Achievement catalogue unavailable; showing IDs with unknown details."
    rows = []
    for item in items:
        entry = catalogue.get(str(item), {})
        if not isinstance(entry, dict):
            entry = {}
        reward = entry.get("reward")
        reward_text = (format_decimal(reward) if isinstance(reward, (int, float, Decimal))
                       and not isinstance(reward, bool) else "Unavailable")
        rows.append((item, plain_html(entry.get("name", "Unknown achievement")),
                     plain_html(entry.get("category", "Unknown")),
                     plain_html(entry.get("description", "No description available")), reward_text))
    result = table_result(f"Achievements for {user}",
                          ["ID", "Achievement", "Category", "Description", "Reward (DUCO)"], rows)
    if note:
        result.data.caption = Text(note)
    return result


@command(name="rates", description="Show exchange prices and reported 24h and 7d changes.",
         category="wallet", example="rates")
def rates() -> CommandResult:
    """
    *rates Show the exchange prices and changes reported by the API.*
    """
    data = get_api().get_user_v3(configured_username()).exchange_rates
    rows = []
    for field in fields(data):
        rate = getattr(data, field.name)
        if rate is None:
            rows.append((field.name, "Unavailable", "Unavailable", "Unavailable"))
            continue
        rows.append((
            field.name,
            format_decimal(rate.price),
            format_decimal(rate.change_24h),
            format_decimal(rate.change_7d),
        ))
    result = table_result(
        "DUCO exchange rates", ["Exchange / currency", "Price", "24h change", "7d change"], rows
    )
    result.data.caption = Text(
        "Display rounded to 12 significant digits. Changes are API values, not percentages."
    )
    return result
