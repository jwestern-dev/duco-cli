#!/usr/bin/env python3
"""Callback, command, and result types shared by the CLI."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


class CommandCallback(Protocol):
    """
    *CommandCallback Callable accepted by the command registry.*
    """

    def __call__(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - signature only
        """
        *__call__ Accept the arguments from command dispatch.*

        args Any - Positional arguments passed to the callback.
        kwargs Any - Keyword arguments passed to the callback.
        """
        ...


@dataclass(slots=True)
class CommandResult:
    """
    *CommandResult Command status, summary and optional data to display.*

    ok bool - Whether the command succeeded.
    message str - Message for the caller.
    data Any - Renderable or other output produced by the command.
    records list[dict[str, Any]] | None - Structured table rows for JSON output.
    """
    ok: bool = True
    message: str = ""
    data: Any = None
    records: list[dict[str, Any]] | None = None

    def __str__(self) -> str:
        """
        *__str__ Use the summary if present, otherwise return ok or error.*
        """
        return self.message if self.message else ("ok" if self.ok else "error")


@dataclass(slots=True)
class Command:
    """
    *Command A callback and the metadata used for dispatch, help and completion.*

    name str - Primary command name.
    description str - Description shown in command help.
    example str - Example invocation shown in help.
    callback CommandCallback - Callable invoked during dispatch.
    id int | None - Optional command identifier.
    module str - Module where the command was registered.
    category str - Command category used for help and dispatch.
    completers Mapping[str, Callable[..., Iterable[str]]] - Argument completion providers indexed by position or option group.
    aliases list[str] - Alternative command names.
    param_names list[str] - Callback parameter names in declaration order.
    requires_verified_user bool - Whether one-shot invocation requires a verified account.
    """

    name: str
    description: str
    example: str
    callback: CommandCallback
    id: int | None = None
    module: str = field(default="", repr=False)
    category: str = "general"
    completers: Mapping[str, Callable[..., Iterable[str]]] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)
    param_names: list[str] = field(default_factory=list)
    requires_verified_user: bool = False

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        """
        *invoke Forward the supplied arguments to the callback.*

        args Any - Positional arguments passed to the callback.
        kwargs Any - Keyword arguments passed to the callback.
        """
        return self.callback(*args, **kwargs)
