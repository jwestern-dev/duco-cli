#!/usr/bin/env python3
"""Command registration, discovery and shared types."""

from __future__ import annotations

from .loader import load_commands
from .registry import CommandRegistry, REGISTRY, command, register_command
from .types import Command, CommandResult, CommandCallback

__all__ = [
    "CommandRegistry",
    "load_commands",
    "Command",
    "CommandResult",
    "CommandCallback",
    "REGISTRY",
    "command",
    "register_command",
]
