"""Browse the public DUCO shop catalogue."""

from collections.abc import Iterable
from urllib.parse import quote

from rich.panel import Panel
from rich.prompt import Confirm
from rich.text import Text

from APISDK import DucoAPIRequestConfig, ShopItem
from APISDK.errors import DucoAPIError, DucoAPIOperationError
from APISDK.parsers import require_success
from core.commands import CommandResult, command
from core.runtime import CONSOLE, configured_username, get_api, require_writes
from core.theme import ACCENT
from core.ui import plain_html, table_result


def item_categories(item: ShopItem) -> str:
    """
    *item_categories Join the item categories for display.*

    item ShopItem - Entry whose categories are displayed.
    """
    if not item.category:
        return "Uncategorized"
    return ", ".join(plain_html(category) for category in item.category)


def price(item: ShopItem) -> str:
    """
    *price Format the listed price in fixed-point notation.*

    item ShopItem - Entry whose price is displayed.
    """
    return format(item.price, "f")


@command(name="items", description="List shop items, descriptions and prices.",
         category="shop", example="items")
def items() -> CommandResult:
    """
    *items List the shop catalogue in item ID order.*
    """
    return catalogue_table("DUCO shop", get_api().get_shop_items())


@command(name="item", description="Show details for a shop item by ID.",
         category="shop", example="item <id>")
def item(identifier: str) -> CommandResult:
    """
    *item Show details for a single shop item.*

    identifier str - Shop item ID.
    """
    item_id = parse_item_id(identifier)
    entry = next((entry for entry in get_api().get_shop_items() if entry.item_id == item_id), None)
    if entry is None:
        return CommandResult(ok=False, message=f"Shop item {item_id} was not found. Use items to browse the shop.")
    return table_result(f"Shop item {entry.item_id}: {plain_html(entry.name)}", ["Field", "Value"], [
        ("ID", entry.item_id), ("Name", plain_html(entry.name)),
        ("Category", item_categories(entry)), ("Price (DUCO)", price(entry)),
        ("Description", plain_html(entry.description)),
        ("Display on profile", "Yes" if entry.display else "No"), ("Icon URL", entry.icon),
    ])


def parse_item_id(identifier: str) -> int:
    """
    *parse_item_id Convert an ASCII item ID to a non-negative integer.*

    identifier str - Item ID as entered at the prompt.
    """
    if not identifier.isascii() or not identifier.isdigit():
        raise ValueError("Item ID must be a non-negative integer.")
    return int(identifier)


def catalogue_table(title: str, entries: Iterable[ShopItem]) -> CommandResult:
    """
    *catalogue_table Build a catalogue table ordered by item ID.*

    title str - Table title.
    entries Iterable[ShopItem] - Entries to show.
    """
    rows = [
        (entry.item_id, plain_html(entry.name), item_categories(entry), price(entry),
         plain_html(entry.description))
        for entry in sorted(entries, key=lambda entry: entry.item_id)
    ]
    return table_result(title, ["ID", "Item", "Category", "Price (DUCO)", "Description"], rows)


def owned_ids(values: Iterable[object]) -> set[int]:
    """
    *owned_ids Convert owned-item values to a set of non-negative IDs.*

    values Iterable[object] - Raw owned-item values from the account response.
    """
    result = set()
    for value in values:
        if isinstance(value, bool):
            raise ValueError("The API returned an unsupported owned-item format.")
        if isinstance(value, int) and value >= 0:
            result.add(value)
        elif isinstance(value, str) and value.isascii() and value.isdigit():
            result.add(int(value))
        else:
            raise ValueError("The API returned an unsupported owned-item format.")
    return result


@command(name="search", description="Search shop item names, descriptions and categories.",
         category="shop", example='shop search "miner"')
def search(*terms: str) -> CommandResult:
    """
    *search Find catalogue entries containing the supplied search text.*

    terms str - Words to join into the search text.
    """
    query = " ".join(terms).strip().casefold()
    if not query:
        raise ValueError("Enter search text, for example: shop search hat")
    matches = []
    for entry in get_api().get_shop_items():
        searchable_text = " ".join((
            plain_html(entry.name),
            plain_html(entry.description),
            item_categories(entry),
        ))
        if query in searchable_text.casefold():
            matches.append(entry)
    return catalogue_table(f"Shop search: {query}", matches)


@command(name="categories", description="List shop categories and item counts.",
         category="shop", example="shop categories")
def categories() -> CommandResult:
    """
    *categories List the categories and count the items assigned to each.*
    """
    counts = {}
    for entry in get_api().get_shop_items():
        for category in set(entry.category or ("Uncategorized",)):
            counts[category] = counts.get(category, 0) + 1
    return table_result("Shop categories", ["Category", "Items"],
                        [(plain_html(key), count) for key, count in sorted(counts.items())])


@command(name="owned", description="List a user's owned shop items.", category="shop",
         example="shop owned [username]", aliases=["inventory"])
def owned(username: str | None = None) -> CommandResult:
    """
    *owned List the items owned by the requested account.*

    username str | None - Account to look up, defaulting to the configured username.
    """
    user = configured_username(username)
    ids = owned_ids(get_api().get_user_v3(user).items)
    catalogue = {entry.item_id: entry for entry in get_api().get_shop_items()} if ids else {}
    rows = []
    for item_id in sorted(ids):
        entry = catalogue.get(item_id)
        rows.append((item_id, plain_html(entry.name) if entry else "Unknown item",
                     item_categories(entry) if entry else "Unknown",
                     plain_html(entry.description) if entry else "Not in current catalogue"))
    return table_result(f"Owned items for {user}", ["ID", "Item", "Category", "Description"], rows)


@command(name="affordable", description="List unowned items within a user's DUCO balance.",
         category="shop", example="shop affordable [username]")
def affordable(username: str | None = None) -> CommandResult:
    """
    *affordable List unowned items within the requested account balance.*

    username str | None - Account to look up, defaulting to the configured username.
    """
    user = configured_username(username)
    account = get_api().get_user_v3(user)
    ids = owned_ids(account.items)
    entries = [entry for entry in get_api().get_shop_items()
               if entry.item_id not in ids and 0 <= entry.price <= account.balance.balance]
    return catalogue_table(f"Unowned items within {user}'s balance ({account.balance.balance} DUCO)", entries)


@command(name="buy", description="Buy a shop item after confirmation.", category="shop", requires_verified_user=True,
         example="shop buy <id>")
def buy(identifier: str) -> CommandResult:
    """
    *buy Confirm and submit a purchase for the verified session account.*

    identifier str - ID of the item to purchase.
    """
    user = require_writes()
    item_id = parse_item_id(identifier)
    username = user.username
    api = get_api()
    entry = next((entry for entry in api.get_shop_items() if entry.item_id == item_id), None)
    if entry is None:
        return CommandResult(ok=False, message=f"Shop item {item_id} was not found.")
    account = api.get_user_v3(username)
    if item_id in owned_ids(account.items):
        return CommandResult(ok=False, message="You already own this item.")
    if not entry.price.is_finite() or entry.price < 0:
        return CommandResult(ok=False, message="The item has an invalid listed price.")
    if account.balance.balance < entry.price:
        return CommandResult(ok=False, message="Insufficient DUCO balance for this item.")
    summary = Text(
        f"Account: {username}\n"
        f"Item: {plain_html(entry.name)} (ID {item_id})\n"
        f"Listed price: {price(entry)} DUCO\n"
        f"Balance: {account.balance.balance} DUCO\n\n"
        "Check the item and price before confirming. The server determines the final price."
    )
    CONSOLE.print(
        Panel(summary, title=Text("Confirm purchase", style=f"bold {ACCENT}"), border_style=ACCENT)
    )
    if not Confirm.ask("Buy this item?", default=False, console=CONSOLE):
        return CommandResult(ok=False, message="Purchase cancelled.")
    try:
        payload = api.request_raw(
            "GET",
            f"shop_buy/{quote(username, safe='')}",
            params={"item": item_id, "password": user.password},
            config=DucoAPIRequestConfig(allow_redirects=False),
        )
        require_success(payload, endpoint="shop_buy")
    except DucoAPIOperationError:
        return CommandResult(
            ok=False,
            message="The API rejected the purchase. Check your account, balance and item availability.",
        )
    except (DucoAPIError, KeyboardInterrupt):
        return CommandResult(
            ok=False,
            message=(
                "Could not confirm the purchase result. Check owned items and balance "
                "before trying again."
            ),
        )
    return CommandResult(message=f"Purchase confirmed by the API: {plain_html(entry.name)} (ID {item_id}).")
