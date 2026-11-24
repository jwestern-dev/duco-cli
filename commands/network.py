"""Network statistics, pools, and the configured user's workers."""

from collections.abc import Sequence
from dataclasses import asdict
from math import fsum
from typing import Any

from APISDK import Miner
from core import runtime
from core.commands import CommandResult, command
from core.runtime import get_api, configured_username
from core.ui import table_result


@command(name="pools", description="List all active mining pools.", category="network",
         aliases=["listpools", "miningpools"])
def pools() -> CommandResult:
    """
    *pools List active mining pools and their reported resource use.*
    """
    items = get_api().get_pools()
    return table_result("Mining pools", ["Name", "Region", "Type", "Connections", "CPU %", "RAM %", "Last sync"],
                        [(p.name, p.region or "Unknown", p.type, p.connections, p.cpu, p.ram, p.last_sync) for p in items])


@command(name="stats", description="List current DUCO statistics.", category="network", aliases=["ducostats"])
def stats() -> CommandResult:
    """
    *stats Display the reported network statistics as a table.*
    """
    data = asdict(get_api().get_statistics())
    rows = []

    def flatten(values: dict[str, Any], prefix: str = "") -> None:
        """
        *flatten Add rows for the leaf values in a nested statistics mapping.*

        values dict[str, Any] - Statistics at the current level.
        prefix str - Display prefix inherited from parent fields.
        """
        for key, value in values.items():
            label = (prefix + key.replace("_", " ")).title()
            if isinstance(value, dict):
                flatten(value, label + " / ")
                continue
            if value is None:
                value = "Unavailable"
            elif isinstance(value, (list, tuple)):
                value = "\n".join(map(str, value))
            rows.append((label, value))

    flatten(data)
    return table_result("DUCO network statistics", ["Statistic", "Value"], rows)


@command(name="rigs", description="List your active mining rigs.", category="network", aliases=["workers", "miners"])
def rigs() -> CommandResult:
    """
    *rigs List the active workers for the configured account.*
    """
    username = configured_username()
    # The user endpoint returns an empty miners list for an idle account,
    # whereas /miners/<username> returns an API failure for the same account.
    items = get_api().get_user(username).miners
    runtime.RIG_IDENTIFIERS = tuple(dict.fromkeys(
        value for worker in items for value in (worker.identifier, worker.threadid) if value
    ))
    return table_result(f"Active workers for {username}",
                        ["Identifier", "Thread", "Software", "Pool", "Algorithm", "H/s", "Accepted", "Rejected"],
                        [(m.identifier, m.threadid, m.software, m.pool, m.algorithm, m.hashrate,
                          m.accepted, m.rejected) for m in items])


@command(name="rig", description="Show details for a worker identifier or thread ID.",
         category="network", example='rig "identifier"', completers={"pos0": lambda: runtime.RIG_IDENTIFIERS})
def rig(identifier: str) -> CommandResult:
    """
    *rig Show every worker matching a rig identifier or thread ID.*

    identifier str - Rig name or thread ID to match.
    """
    username = configured_username()
    items = get_api().get_user(username).miners
    matches = [item for item in items if item.identifier == identifier or item.threadid == identifier]
    if not matches:
        return CommandResult(ok=False, message=f"No active worker matches {identifier!r}. Use rigs to list workers.")
    # A rig identifier can be shared by multiple threads; show every match.
    rows = []
    for item in matches:
        for key, value in asdict(item).items():
            rows.append((item.threadid, key.replace("_", " ").title(),
                         "Not set" if value is None else value))
    return table_result(f"Worker details for {identifier}", ["Thread", "Field", "Value"], rows)


@command(name="hashrate", description="Summarise your workers' hashrate and shares by algorithm.",
         category="network", example="hashrate")
def hashrate() -> CommandResult:
    """
    *hashrate Summarise worker throughput and share counts by algorithm.*
    """
    username = configured_username()
    items = get_api().get_user(username).miners
    groups = {}
    for item in items:
        groups.setdefault(item.algorithm, []).append(item)
    rows = []

    def summary(label: str, workers: Sequence[Miner]) -> tuple[str, int, str, int, int, str]:
        """
        *summary Build one row of worker counts, throughput, and share statistics.*

        label str - Algorithm or total label.
        workers Sequence[Miner] - Workers included in the summary.
        """
        accepted = sum(item.accepted for item in workers)
        rejected = sum(item.rejected for item in workers)
        total = accepted + rejected
        return (label, len(workers), f"{fsum(item.hashrate for item in workers):,.2f}",
                accepted, rejected, f"{100 * rejected / total:.2f}%" if total else "N/A")

    for algorithm, workers in sorted(groups.items()):
        rows.append(summary(algorithm, workers))
    rows.append(summary("Total reported", items))
    return table_result(f"Worker totals for {username}",
                        ["Algorithm", "Workers", "H/s", "Accepted", "Rejected", "Reject %"], rows)


@command(name="richlist", description="Show the top ten richest accounts reported by the network.",
         category="network", example="richlist")
def richlist() -> CommandResult:
    """
    *richlist Display the ten richest accounts reported by the API.*
    """
    items = get_api().get_statistics().top_10_richest_miners
    return table_result("Top ten richest accounts", ["Rank", "Account / balance (API)"],
                        [(rank, item) for rank, item in enumerate(items[:10], start=1)])
