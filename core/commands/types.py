#!/usr/bin/env python3
"""Callback, command, and result types shared by the CLI."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


class CommandCallback(Protocol):
    """Callable accepted by the command registry."""

    def __call__(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - signature only
        """Accept the arguments from command dispatch."""
        ...


@dataclass(slots=True)
class CommandResult:
    """Command status, summary and optional data to display."""
    ok: bool = True
    message: str = ""
    data: Any = None

    def __str__(self) -> str:
        """Use the summary if present, otherwise return ok or error."""
        return self.message if self.message else ("ok" if self.ok else "error")


@dataclass(slots=True)
class Command:
    """A callback and the metadata used for dispatch, help and completion."""

    name: str
    description: str
    example: str
    callback: CommandCallback
    id: int | None = None
    module: str = field(default="", repr=False)
    category: str = "general"
    completers: Mapping[str, Callable[..., object]] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)
    param_names: list[str] = field(default_factory=list)

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        """Forward the supplied arguments to the callback."""
        return self.callback(*args, **kwargs)
