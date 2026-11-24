# Changelog

## 1.0.0 — 2026-11-24

### Added

- Run a single command from the terminal, for example `python run.py balance alice`. Public lookups skip wallet login. Sending DUCO and buying items still require account verification and confirmation.
- Use `--json` in scripts to receive one object with `ok`, `message`, and `data`. Tables become arrays of records, confirmation prompts go to stderr, and a failed command returns a nonzero exit code.
- Filter recent transactions by direction (`--incoming` or `--outgoing`), sender (`--from`), or recipient (`--to`). Use `--limit 1` through `--limit 1000` to choose how many recent entries to search. The results show how many entries were searched and how many matched.
- Complete commands and aliases with Tab in the interactive shell. Completion also suggests configuration actions, transaction filters, and worker names and thread IDs from the latest `rigs` lookup.
- Chain shell commands with `&&` to continue on success, `||` to continue on failure, or `;` to continue unconditionally. Chains run from left to right.
- Run `restart` inside the shell to reload settings with the same startup options.
- Use `--debug` to append startup checks, command outcomes, API request timings, HTTP status codes, and error locations to `debug.log` in the working directory. The log omits command arguments, credentials, and request payloads.

### Changed

- Interactive startup checks the installed version against the published `VERSION` file and tests the API routes used by the CLI. Transfer and purchase checks use credential-free `OPTIONS` requests. The session panel shows the active account and access mode, with any update or endpoint warnings beneath it.
- Help tables highlight aliases and examples and suggest how to open more detailed help.
- Wallet login retries once when the API reports an invalid password, a response the service can also return for an internal error.
- On Windows, `DucoCLI.cmd` returns directly to the caller after a failed command when launched with arguments. Scripts can inspect the exit code without waiting for a keypress.

### Fixed

- Preserve incoming monetary amounts through JSON decoding and reject non-finite balances, prices and transaction amounts.
- Declining a transfer or purchase returns an unsuccessful status for scripts and shell chains. Transfer previews enforce a 128-digit fixed-point limit.
- Transaction filters use at most the newest requested entries. Short responses report the requested and searched counts.
- Passwordless profiles display read-only access in one-shot mode. Both `config show` and `config config show` work.
- SDK-created sessions apply the configured headers, and connection errors omit the underlying request URL.

### Upgrading from 0.1.0

- Run `python -m pip install -r requirements.txt` in your DucoCLI environment to install the updated dependencies, including `prompt-toolkit` for the interactive shell.
- Existing `settings.toml` files still load. DucoCLI ignores the old `user.mining_key` field, omits it when saving settings, and no longer asks for it during setup or displays it in `config show`.

[0.1.0 source used for this comparison](https://github.com/jwestern-dev/duco-cli/tree/6e30bc6bbc8c5f496067403ee3e8eaf981f2a49e)
