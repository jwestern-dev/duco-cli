# DucoCLI

**Version 1.0.0 · Python 3.11+ · MIT**

DucoCLI is a Python command-line wallet and monitoring tool for [Duino-Coin](https://duinocoin.com/). Check your DUCO balance and transaction history, send funds, shop for items, and see how your mining rigs are performing from one terminal.

## Features

- **Wallet** — Check balances and profiles, look up transactions by ID or hash, and send DUCO with a confirmation prompt.
- **Shop** — Browse or search the catalogue, check which items you own or can afford, and confirm purchases.
- **Network** — View network statistics, active mining pools, and the reported rich list.
- **Mining rigs** — List active workers, inspect individual rigs, and see hashrate and accepted and rejected shares by algorithm.
- **Account data** — View achievements and reported exchange rates.

## Quick start

You’ll need Python 3.11 or newer, an internet connection for API requests, and a Duino-Coin account. Clone the repository or download the source from GitHub.

```powershell
git clone https://github.com/jwestern-dev/duco-cli.git
cd duco-cli
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\DucoCLI.cmd
```

`DucoCLI.cmd` uses the local `.venv` when present. You can also run `python run.py` directly with the Python interpreter where you installed the dependencies.

On first launch, enter your DUCO username and optionally your wallet password. DucoCLI writes `settings.toml` beside `run.py`. Leave the wallet password blank to use read-only mode.

## Commands

Interactive startup shows the boot checks first, clears the terminal, and displays the account, access mode, and keyboard hints. It compares the installed version with the project's published `VERSION` and checks the API routes used by the CLI. Read endpoints are checked with the SDK. The transfer and purchase routes receive credential-free `OPTIONS` requests to check the methods they advertise. Account login runs through the regular startup flow. Update notices and endpoint warnings remain visible below the account panel. One-shot commands and piped input skip these network diagnostics.

Type `help` at the DucoCLI prompt to see command categories. Use `help wallet` to browse one category or `help wallet send` for usage and aliases.

The interactive prompt suggests commands and aliases as you type. Type `ach` and press Tab to fill in `achievements`, then Enter to run it. Suggestions also work inside categories, such as `wallet ach`.

Tab also completes `config` actions and `transactions` filters. After running `rigs`, use Tab after `rig ` to select a worker name or thread ID from those results. Type `restart` to reload settings and open a fresh session with the same startup options.

Inside the interactive shell, `profile user123 && profile user456` runs the second lookup if the first succeeds. Use `||` to run a command after a failure, or `;` to run the next command regardless. DucoCLI evaluates chains from left to right. Quote operators to include them in an argument, as in `shop search "Alice && Bob"`. Suggestions and Tab completion work after each operator and refresh when you press Backspace.

### Run a single command

Pass a command to the launcher to run it once and exit. Public lookups skip wallet login. Sending and buying still require a verified account and confirmation.

```shell
python run.py balance alice
python run.py rigs --json
python run.py transactions alice --incoming --from bob --limit 50 --json
```

`--incoming` and `--outgoing` are relative to the queried account. Combine either with `--from USER` or `--to USER`. Filters search the recent entries returned by the API. The default search depth comes from `cli.transaction_limit` (10 by default). Override it with `--limit 1` through `--limit 1000`. The result reports how many entries were searched and matched, and the requested limit when the API returns fewer entries.

With `--json`, stdout contains one object with `ok`, `message`, and `data`. Tables become arrays of records keyed by column name. Exact decimal amounts are strings. Confirmation prompts go to stderr. Failed commands return a nonzero exit status. Use `--` before command text that must be passed literally, such as `python run.py --json -- shop search --version`.

| Task | Commands |
| --- | --- |
| Check your wallet | `balance`, `profile`, `transactions` |
| Look up a transfer | `transaction 123`, `transaction hash:<hash>` |
| Send DUCO | `send <recipient> <amount> "optional memo"` |
| Explore the shop | `shop items`, `shop search hat`, `shop item 1` |
| Check your inventory or buy an item | `shop owned`, `shop affordable`, `shop buy 1` |
| Check the network | `stats`, `pools`, `richlist` |
| Inspect mining rigs | `rigs`, `rig "my worker"`, `hashrate` |
| View account extras | `achievements`, `rates` |
| Inspect settings or exit | `config show`, `version`, `quit` |

Wallet queries use your configured account by default. Commands such as `balance` and `transactions` also accept a username.

Transfers and purchases show a preview and default to **No** at the confirmation prompt. Declining either action returns an unsuccessful command status. Transfers accept up to 128 digits in fixed-point notation. DucoCLI submits each confirmed request once. If a transfer or purchase comes back unconfirmed, check your transaction history or inventory before trying again.

See the [command reference](commands/README.md) for the full list.

## Configuration

Use `DucoCLI.cmd --setup` to run account setup again. Use `--check-config` to validate the TOML file locally, or `--read-only` to skip the startup login and disable sending and buying.

| Option | Purpose |
| --- | --- |
| `--setup` | Create or replace settings through an interactive prompt. |
| `--check-config` | Validate the settings file locally and exit. |
| `--read-only` | Open the shell with spending disabled. API commands still require connectivity. |
| `--settings <path>` | Use a different TOML file. |
| `--version` | Print the installed version. |
| `--debug` | Append timestamped diagnostics to `debug.log` in the working directory. |
| `--json` | Emit a machine-readable result for a one-shot command, version, or configuration check. |

Run `DucoCLI.cmd --debug` or `python run.py --debug` to record startup checks, command names and outcomes, request timing and HTTP status codes, and error locations. Debug output goes only to the file. Command arguments, wallet credentials, and HTTP payloads are omitted.

Inside the shell, `config show` displays masked settings and `config check` checks the account with the API.

**Keep `settings.toml` private.** DucoCLI stores the wallet password as plain text in this local file. Leave it out of commits, screenshots, and issue reports.

## Source layout

| Path | Purpose |
| --- | --- |
| [`APISDK/`](APISDK/) | Duino-Coin REST client and response models. |
| [`core/`](core/) | Startup, settings, command dispatch, and terminal output. |
| [`commands/`](commands/) | Wallet, network, shop, and system commands. |
| [`run.py`](run.py) | Python entry point. |
| [`DucoCLI.cmd`](DucoCLI.cmd) | Windows launcher. |

## Licence

DucoCLI is licensed under the MIT License.
