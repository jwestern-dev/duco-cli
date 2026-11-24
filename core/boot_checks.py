"""Non-mutating startup checks for the routes used by DucoCLI."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from urllib.parse import quote

import requests

from APISDK import DucoAPI, DucoAPIConfig
from APISDK.errors import DucoAPIError
from APISDK.parsers import require_success
from core.debug import LOGGER
from core.ui import boot_status
from core.version import __version__


VERSION_URL = "https://raw.githubusercontent.com/jwestern-dev/duco-cli/refs/heads/main/VERSION"
# Public ledger entry from the SDK's transaction fixtures.
FIRST_TX_HASH = "84b2303d95bcd1dd921350803ae92157d667d627"


def check_version(timeout):
    """
    *check_version Compare the installed version with the published version.*

    timeout float - HTTP request timeout in seconds.
    """
    with requests.get(VERSION_URL, timeout=timeout) as response:
        response.raise_for_status()
        remote = response.text.strip()
    if not re.fullmatch(r"[0-9]{1,9}\.[0-9]{1,9}\.[0-9]{1,9}", remote):
        raise ValueError("unexpected VERSION format")
    installed = tuple(map(int, __version__.split(".")))
    published = tuple(map(int, remote.split(".")))
    if installed == published:
        return "OK", f"DucoCLI {__version__} matches the published version"
    if installed < published:
        return "WARN", f"DucoCLI {remote} is available (installed {__version__})"
    return "WARN", f"Local DucoCLI {__version__} is ahead of published {remote}"


def achievements(api):
    """
    *achievements Check that the achievements endpoint returns a catalogue.*

    api DucoAPI - Client used for the endpoint check.
    """
    result = require_success(api.request_raw("GET", "achievements"), endpoint="achievements")
    return isinstance(result.result, dict)


def advertises_get(api, path):
    """
    *advertises_get Inspect a spending route's allowed methods using an OPTIONS request.*

    api DucoAPI - Client used for the endpoint check.
    path str - Relative API route to inspect.
    """
    # These two routes spend funds even though the server implements them as GET.
    with api.transport.session.options(api.config.endpoint_url(path), timeout=api.config.timeout,
                                       allow_redirects=False) as response:
        methods = response.headers.get("Allow", "").upper().split(",")
        return 200 <= response.status_code < 300 and "GET" in {method.strip() for method in methods}


def check_endpoints(console, settings):
    """
    *check_endpoints Run the startup checks concurrently and collect notices for the session panel.*

    console Console - Console receiving output or prompts.
    settings Settings - Account settings and CLI preferences.
    """
    user = settings.user.username
    timeout = min(settings.timeout, 3.0)
    checks = {
        "/balances/<user>": lambda api: api.get_balance(user),
        "/users/<user>": lambda api: api.get_user(user),
        "/v3/users/<user>": lambda api: api.get_user_v3(user),
        "/user_transactions/<user>": lambda api: api.get_user_transactions(user, limit=1),
        "/transactions/<hash>": lambda api: api.get_transaction(FIRST_TX_HASH).id == 1,
        "/id_transactions/<id>": lambda api: api.get_transaction_by_id(1).hash == FIRST_TX_HASH,
        "/statistics": lambda api: api.get_statistics(),
        "/all_pools": lambda api: api.get_pools(),
        "/shop_items": lambda api: api.get_shop_items(),
        "/achievements": achievements,
        "/transaction/ (OPTIONS only)": lambda api: advertises_get(api, "transaction/"),
        "/shop_buy/<user> (OPTIONS only)": lambda api: advertises_get(api, f"shop_buy/{quote(user, safe='')}"),
    }

    def probe(path, check):
        """
        *probe Run one endpoint check with its own short-lived client.*

        path str - Endpoint label shown in diagnostics.
        check Callable[[DucoAPI], object] - Endpoint check to run with a fresh client.
        """
        with DucoAPI(config=DucoAPIConfig(timeout=timeout)) as api:
            if check(api) is False:
                return "WARN", f"{path}: unexpected response"
        return "OK", path

    notices = []
    boot_status(console, "WAIT", "Checking published version and API endpoints…")
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(check_version, timeout): "Published version"}
        jobs.update({pool.submit(probe, path, check): path for path, check in checks.items()})
        for job in as_completed(jobs):
            try:
                status, detail = job.result()
            except (requests.RequestException, DucoAPIError, ValueError) as exc:
                status = "WARN"
                code = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)
                reason = f"HTTP {code}" if code else type(exc).__name__
                detail = f"{jobs[job]}: check unsuccessful ({reason})"
            boot_status(console, status, detail)
            LOGGER.debug("Boot check %s: %s", status, detail)
            if status != "OK":
                notices.append(detail)
    return notices
