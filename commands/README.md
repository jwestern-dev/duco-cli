# DucoCLI commands

Start the prompt from the DucoCLI directory with `python run.py`.

Add Python modules to this directory (nested packages need `__init__.py`).
The loader imports them at startup; underscore-prefixed modules are skipped.
Module import errors stop startup so broken commands are visible.

```python
from core.commands import CommandResult, command

@command(
    name="balance",
    description="Show the wallet balance",
    example="wallet balance",
    category="wallet",
    aliases=["bal"],
)
def balance() -> CommandResult:
    """
    *balance Show the wallet balance.*
    """
    return CommandResult(message="Balance implementation goes here")
```

Names and aliases are globally unique and case-insensitive, matching the
reference registry. Both `balance` and `wallet balance` dispatch this command.
The decorator preserves the function and records its signature and module.
Callbacks receive string arguments; convert values inside the callback as needed.
Return `CommandResult`, another printable value, or `None` for no output.

Help comes from command metadata: `help`, `help wallet`, `help wallet balance`.
Register category descriptions with `REGISTRY.set_category_description(...)`.
Imports are cached, so loading twice does not duplicate registrations.

## Account settings

Run `python run.py --setup` in a terminal and enter your username. Supply a wallet password to enable spending. Settings are resolved
relative to the application directory, regardless of the current directory.
No settings are needed for public network queries or an explicit username.

## Built-in commands

| Command | Aliases | Purpose |
| --- | --- | --- |
| `help [category] [command]` | | All commands, category help, or command help; `help balance` also works |
| `quit` | `close`, `leave`, `shutdown`, `exit` | Close the application |
| `restart` | | Restart the interactive session and reload the current settings file |
| `clear` | `cls` | Clear the terminal |
| `version` | | Application and Python versions |
| `config [show/check/setup]` | | Masked settings, account checks and interactive setup |
| `transactions [username] [--incoming/--outgoing] [--from USER] [--to USER] [--limit N]` | `gettransactions`, `listtransactions` | Filter recent entries by direction, sender or recipient. Search up to N entries (1–1000). |
| `balance [username]` | `bal` | Balance and stake amount |
| `profile [username]` | | Account details, verification, trust and miner limit |
| `transaction <id-or-hash>` | | Transaction lookup; `hash:12345678` forces a numeric hash |
| `achievements [username]` | | Achievement names, descriptions, categories and reward amounts |
| `rates` | | Exchange prices and raw 24h/7d changes for the configured account |
| `send username amount [memo]` | | Transfer DUCO after confirmation |
| `pools` | `listpools`, `miningpools` | Available mining pools |
| `stats` | `ducostats` | Current network statistics |
| `rigs` | `workers`, `miners` | Active workers for the configured user |
| `rig <identifier>` | | Full details for all matching workers, or one thread ID |
| `hashrate` | | Per-algorithm and total reported hashrate, shares and reject percentage |
| `richlist` | | Top ten richest account entries reported by the API |
| `items` | | Browse shop item IDs, descriptions, categories and exact DUCO prices |
| `item <id>` | | Full details for a shop item, including display flag and icon URL |
| `search <text...>` | | Search shop names, descriptions and categories |
| `categories` | | Count items in each shop category |
| `owned [username]` | `inventory` | List owned items, including unknown catalogue IDs |
| `affordable [username]` | | List unowned items within the account balance |
| `buy <id>` | | Buy an item with a default-No confirmation |

Wallet queries default to the configured username
`send user123 10.5 Happy Birthday!`. Amounts are parsed directly as Decimal.
The transfer prompt defaults to No. Requests are never automatically retried by
these commands; if a transfer result cannot be confirmed, inspect transactions
before sending again.

Output uses Rich tables with literal API text and no emojis. Install dependencies
with `python -m pip install -r requirements.txt` (Python 3.11 or newer).
The transfer endpoint follows the official API documentation:
https://github.com/duino-coin/duco-rest-api#api-endpoints

Startup now validates settings, offers first-run setup and verifies the account.
Use `--read-only` to skip login and disable spending. See the root README for installation.


## Colour standard

The shared theme lives in `core/theme.py`:

- Primary `#FC6803`: titles, headers, prompt, success messages.
- Secondary `#EE5A24`: borders and error messages.
- Accent `#FF9F43`: information and confirmation prompts.

Use the named `duco.*` Rich styles with the shared console. For renderables
that may be printed by other consoles, use the palette constants directly.

Rates use ordinary decimal notation, rounded to 12 significant digits for display.
Changes remain absolute API values, without interpreting them as percentages.
SDK values and transfer amounts are unaffected.
Achievement details are fetched from the official `/achievements` catalogue. Unknown IDs
remain visible; if the catalogue cannot be fetched, the table includes a warning.
Use `rig "name with spaces"` for shared identifiers; all matching threads are shown.
Hashrate totals sum reported H/s, with separate rows for each algorithm. Share counts
reflect currently active workers, rather than account lifetime totals.

Shop browsing also supports `shop items` and `shop item 1`, without account
configuration. Descriptions are converted from HTML to plain text. The catalogue
includes items with `display=false`; that flag describes profile display, not
purchase availability.

Use `shop search hat`, `shop categories`, `shop owned`, `shop affordable`,
and `shop buy 1` (the `shop` prefix is optional). Purchases use the configured
username and password. The CLI checks ownership and funds first, then displays
the listed price for confirmation. The API determines the final price and
availability; the affordable list is a balance filter, not a purchase guarantee.
A purchase is submitted once; uncertain outcomes require checking inventory and
balance before retrying. No purchase is performed just by browsing.

The official wallet implements purchases via `/shop_buy/<username>` and reads
owned item IDs from the v3 user response. Cosmetic display toggles are local
browser preferences rather than account API operations. No supported sell,
refund, or item-transfer operation was found in the reviewed shop interface.
Source: https://github.com/duino-coin/duco-webservices/blob/master/2023/js/main.js
