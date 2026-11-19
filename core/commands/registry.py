#!/usr/bin/env python3
"""Command registration, aliases, and help metadata."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import inspect
from typing import Any

from .types import Command


class CommandRegistry:
    """Case-insensitive command lookup and category metadata for help."""

    def __init__(self) -> None:
        """Start with an empty set of commands, aliases and categories."""
        self._commands_by_name: dict[str, Command] = {}
        self._alias_to_primary: dict[str, str] = {}
        self._category_descriptions: dict[str, str] = {}

    def register(self, command_obj: Command) -> None:
        """Register a command after checking all its names for collisions."""
        primary_key = command_obj.name.lower()

        if primary_key in self._commands_by_name or primary_key in self._alias_to_primary:
            raise ValueError(f"Command '{command_obj.name}' already registered.")

        # Validate every alias before changing registry state.
        alias_keys = [alias.lower() for alias in command_obj.aliases]
        seen = {primary_key}
        for alias, alias_key in zip(command_obj.aliases, alias_keys):
            if (
                alias_key in seen
                or alias_key in self._commands_by_name
                or alias_key in self._alias_to_primary
            ):
                raise ValueError(
                    f"Alias '{alias}' for '{command_obj.name}' collides with an existing name."
                )
            seen.add(alias_key)
        self._commands_by_name[primary_key] = command_obj
        for alias_key in alias_keys:
            self._alias_to_primary[alias_key] = primary_key

    def get(self, name: str) -> Command | None:
        """Look up a command by its name or an alias."""
        key = name.lower()
        if key in self._commands_by_name:
            return self._commands_by_name[key]
        if key in self._alias_to_primary:
            return self._commands_by_name[self._alias_to_primary[key]]
        return None

    def all(self) -> list[Command]:
        """List each registered command once, in registration order."""
        return list(self._commands_by_name.values())

    def names(self) -> list[str]:
        """List command names and aliases for completion."""
        return [*self._commands_by_name.keys(), *self._alias_to_primary.keys()]

    def categories(self) -> dict[str, list[Command]]:
        """Group commands for help, including categories with no commands."""
        grouped: dict[str, list[Command]] = {
            category: [] for category in self._category_descriptions
        }
        for cmd in self._commands_by_name.values():
            grouped.setdefault(cmd.category, []).append(cmd)
        return grouped

    def set_category_description(self, category: str, description: str) -> None:
        """Set the help text for a category."""
        self._category_descriptions[category.lower()] = description.strip()

    def get_category_description(self, category: str) -> str:
        """Return the category's help text, or an empty string."""
        return self._category_descriptions.get(category.lower(), "")


REGISTRY = CommandRegistry()


def command(
    *,
    name: str | None = None,
    description: str | None = None,
    example: str | None = None,
    id: int | None = None,
    category: str | None = None,
    completers: Mapping[str, Callable[..., object]] | None = None,
    aliases: list[str] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a callback and return the original function.

    The default name is the function name with underscores replaced by
    hyphens. The callback docstring supplies help text when description is
    omitted. The registry keeps the argument names for completion.
    """

    def wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
        """Record the callback alongside its help and completion metadata."""
        signature = inspect.signature(func)
        param_names = [p.name for p in signature.parameters.values()]

        command_obj = Command(
            name=(name or func.__name__).replace("_", "-"),
            description=(description or (func.__doc__ or "")).strip(),
            example=example or "",
            id=id,
            callback=func,
            category=category or "general",
            completers=completers or {},
            aliases=aliases or [],
            param_names=param_names,
        )
        command_obj.module = func.__module__
        REGISTRY.register(command_obj)
        return func

    return wrapper


def register_command(command_obj: Command) -> None:
    """Register a pre-built command in the shared registry."""
    REGISTRY.register(command_obj)
