"""Table rendering and formatting for terminal output."""

from collections.abc import Iterable, Sequence
from decimal import Decimal, localcontext
from html.parser import HTMLParser

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from core.commands import CommandResult
from core.theme import ACCENT, PRIMARY


STARTUP_BANNER = r"""  ___                 ___ _    ___
 |   \ _  _ __ ___   / __| |  |_ _|
 | |) | || / _/ _ \ | (__| |__ | |
 |___/ \_,_\__\___/  \___|____|___|"""


def session_panel(username: str, mode: str, version: str, interactive: bool) -> Panel:
    """
    *session_panel Show the active account and the shortcuts available in this session.*

    username str - DUCO account name.
    mode str - Access mode shown for the current session.
    version str - Installed DucoCLI version.
    interactive bool - Whether to show keyboard shortcuts.
    """
    heading = Text.assemble(("DucoCLI", f"bold {PRIMARY}"), (f"  v{version}", "dim"))
    body = Text.assemble((username, "bold"), "  /  ", mode, "\n\n",
                         ("help", f"bold {ACCENT}"), "  Browse commands")
    if interactive:
        body.append("\n")
        body.append("Tab", style=f"bold {ACCENT}")
        body.append("   Complete a command")
    return Panel.fit(body, title=heading, title_align="left", box=box.ROUNDED,
                     border_style=PRIMARY, padding=(0, 1))


def boot_status(console: Console, label: str, message: str) -> None:
    """
    *boot_status Print a labelled progress message during startup.*

    console Console - Console receiving output or prompts.
    label str - Label to display.
    message str - Message for the caller.
    """
    colours = {"OK": "green", "WAIT": "yellow", "WARN": "yellow", "SKIP": "cyan", "FAIL": "red"}
    console.print(Text.assemble((f"[ {label} ]", f"bold {colours[label]}"), " ", message))


def table_result(
    title: str,
    columns: Sequence[str],
    rows: Iterable[Iterable[object]],
    message: str = "",
    *,
    hint: str = "",
) -> CommandResult:
    """
    *table_result Build a Rich table with literal text in its title, headings and cells.*

    title str - Title above the table.
    columns Sequence[str] - Column headings in display order.
    rows Iterable[Iterable[object]] - Values for each table row.
    message str - Message for the caller.
    hint str - Optional guidance below the table.
    """
    table = Table(
        title=Text(title, style=f"bold {PRIMARY}"),
        title_justify="left",
        title_style="none",
        header_style="bold",
        box=box.SIMPLE,
        pad_edge=False,
        border_style="dim",
        caption=Text(hint) if hint else None,
        caption_style="dim",
        caption_justify="left",
    )
    for column in columns:
        table.add_column(Text(column))
    records = []
    for row in rows:
        record = dict(zip(columns, row, strict=True))
        records.append(record)
        table.add_row(*(Text(str(value)) for value in record.values()))
    if not records:
        table.add_row(Text("No results", style="dim"), *(Text("") for _ in columns[1:]))
    return CommandResult(message=message or title, data=table, records=records)


def format_decimal(value: Decimal | int | float | str, significant_digits: int = 12) -> str:
    """
    *format_decimal Round to significant digits for display and omit exponent notation.*

    value Decimal | int | float | str - Number to round for display.
    significant_digits int - Number of significant digits to retain for display.
    """
    with localcontext() as context:
        context.prec = significant_digits
        rounded = +Decimal(str(value))
    text = format(rounded, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if rounded == 0 else text


def plain_html(value: object) -> str:
    """
    *plain_html Collect the text from a description and collapse whitespace.*

    value object - Description whose HTML tags should be removed.
    """

    class TextParser(HTMLParser):
        """
        *TextParser Preserve spacing between blocks while collecting text fragments.*
        """

        def __init__(self) -> None:
            """
            *__init__ Start with an empty list of text fragments.*
            """
            super().__init__(convert_charrefs=True)
            self.parts = []

        def handle_data(self, data: str) -> None:
            """
            *handle_data Collect text emitted by HTMLParser.*

            data str - Text fragment between HTML tags.
            """
            self.parts.append(data)

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            """
            *handle_starttag Separate text at the start of a block or line break.*

            tag str - HTML element name.
            attrs list[tuple[str, str | None]] - Attributes on the opening element.
            """
            if tag in ("br", "p", "li", "div"):
                self.parts.append(" ")

        def handle_endtag(self, tag: str) -> None:
            """
            *handle_endtag Separate text at the end of a block.*

            tag str - HTML element name.
            """
            if tag in ("p", "li", "div"):
                self.parts.append(" ")

    parser = TextParser()
    parser.feed(str(value))
    return " ".join("".join(parser.parts).split())
