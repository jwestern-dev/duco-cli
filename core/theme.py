"""Official Duino-Coin palette and shared Rich styles."""

from rich.theme import Theme

PRIMARY = "#FC6803"
SECONDARY = "#EE5A24"
ACCENT = "#FF9F43"

THEME = Theme(
    {
        "duco.title": f"bold {PRIMARY}",
        "duco.header": f"bold {PRIMARY}",
        "duco.border": SECONDARY,
        "duco.prompt": f"bold {PRIMARY}",
        "duco.info": ACCENT,
        "duco.success": "default",
        "duco.warning": f"bold {ACCENT}",
        "duco.error": "bold red",
    }
)
