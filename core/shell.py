"""Control operators for the interactive DucoCLI command line."""

import shlex
from collections.abc import Iterator


def operators(line: str) -> Iterator[tuple[int, str]]:
    """
    *operators Find unquoted operators without removing quotes or escapes from arguments.*

    line str - Shell input before quote and escape processing.
    """
    quote = ""
    index = 0
    while index < len(line):
        char = line[index]
        if char == "\\" and quote != "'":
            index += 2
            continue
        if quote:
            if char == quote:
                quote = ""
        elif char in "'\"":
            quote = char
        elif char in ";&|":
            op = line[index:index + 2]
            if op not in {"&&", "||"}:
                op = char
            yield index, op
            index += len(op)
            continue
        index += 1


def parse_chain(line: str) -> list[tuple[str, list[str]]]:
    """
    *parse_chain Parse the complete line before any of its commands can run.*

    line str - Shell input before quote and escape processing.
    """
    chain = []
    start = 0
    condition = ";"
    for index, op in operators(line):
        if op not in {"&&", "||", ";"}:
            raise ValueError(f"Unsupported operator {op!r}. Use &&, || or ;, or quote it as text.")
        words = shlex.split(line[start:index])
        if not words:
            raise ValueError(f"Expected a command before {op!r}.")
        chain.append((condition, words))
        start = index + len(op)
        condition = op
    words = shlex.split(line[start:])
    if words:
        chain.append((condition, words))
    elif condition != ";":
        raise ValueError(f"Expected a command after {condition!r}.")
    return chain
