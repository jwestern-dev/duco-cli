"""Table rendering and formatting for terminal output."""

from collections.abc import Iterable, Sequence
from decimal import Decimal, localcontext
from html.parser import HTMLParser

from rich.table import Table
from rich.text import Text

from core.commands import CommandResult
from core.theme import PRIMARY, SECONDARY


def table_result(
    title: str,
    columns: Sequence[str],
    rows: Iterable[Iterable[object]],
    message: str = "",
) -> CommandResult:
    """Build a Rich table with literal text in its title, headings and cells."""
    table = Table(
        title=Text(title, style=f"bold {PRIMARY}"),
        header_style=f"bold {PRIMARY}",
        border_style=SECONDARY,
    )
    for column in columns:
        table.add_column(Text(column))
    count = 0
    for row in rows:
        table.add_row(*(Text(str(value)) for value in row))
        count += 1
    if not count:
        table.add_row(Text("No results"), *(Text("") for _ in columns[1:]))
    return CommandResult(message=message or title, data=table)


def format_decimal(value: Decimal | int | float | str, significant_digits: int = 12) -> str:
    """Round to significant digits for display and omit exponent notation."""
    with localcontext() as context:
        context.prec = significant_digits
        rounded = +Decimal(str(value))
    text = format(rounded, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if rounded == 0 else text


def plain_html(value: object) -> str:
    """Collect the text from a description and collapse whitespace."""

    class TextParser(HTMLParser):
        """Preserve spacing between blocks while collecting text fragments."""

        def __init__(self) -> None:
            """Start with an empty list of text fragments."""
            super().__init__(convert_charrefs=True)
            self.parts = []

        def handle_data(self, data: str) -> None:
            """Collect text emitted by HTMLParser."""
            self.parts.append(data)

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            """Separate text at the start of a block or line break."""
            if tag in ("br", "p", "li", "div"):
                self.parts.append(" ")

        def handle_endtag(self, tag: str) -> None:
            """Separate text at the end of a block."""
            if tag in ("p", "li", "div"):
                self.parts.append(" ")

    parser = TextParser()
    parser.feed(str(value))
    return " ".join("".join(parser.parts).split())
