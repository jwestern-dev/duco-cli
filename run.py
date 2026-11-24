"""DucoCLI entry point."""

import sys


def launch() -> int | str | None:
    """
    *launch Run the CLI and report missing dependencies without a traceback.*
    """
    if sys.version_info < (3, 11):
        print("DucoCLI requires Python 3.11 or newer.")
        return 1
    try:
        from core.cli import main
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.split(".")[0] in {
            "rich", "requests", "urllib3", "charset_normalizer", "certifi", "idna",
            "prompt_toolkit", "wcwidth",
        }:
            print("Dependencies are missing. Run: python -m pip install -r requirements.txt")
            return 1
        print("The installation is incomplete. Restore the DucoCLI application files.")
        return 1
    try:
        return main(sys.argv[1:])
    except SystemExit as exc:
        return exc.code
    except Exception:
        print("DucoCLI could not start. Check installation files and settings permissions.")
        return 1


if __name__ == "__main__":
    raise SystemExit(launch())
