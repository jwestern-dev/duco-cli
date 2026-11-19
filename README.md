# DucoCLI

**Version 1.0 · Python 3.11+ · MIT**

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
python.exe -m pip install "requests>=2.31,<3" "rich>=13,<15"
.\DucoCLI.cmd
```

`DucoCLI.cmd` uses the local `.venv` when present. You can also run `python run.py` directly with the Python interpreter where you installed the dependencies.

On first launch, enter your DUCO username and optionally your wallet password and mining key. DucoCLI writes `settings.toml` beside `run.py`. Leave the wallet password blank to use read-only mode.

## Commands

Type `help` at the DucoCLI prompt to see command categories. Use `help wallet` to browse one category or `help wallet send` for usage and aliases.

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

Transfers and purchases show a preview and default to **No** at the confirmation prompt. DucoCLI submits each confirmed request once. If a transfer or purchase comes back unconfirmed, check your transaction history or inventory before trying again.

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

Inside the shell, `config show` displays masked settings and `config check` checks the account with the API.

**Keep `settings.toml` private.** DucoCLI stores the wallet password and mining key as plain text in this local file. Leave it out of commits, screenshots, and issue reports.

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
