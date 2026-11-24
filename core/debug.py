"""File-only diagnostics for a DucoCLI session."""

import logging
import platform
from contextlib import contextmanager
from pathlib import Path
from traceback import walk_tb

from core.version import __version__

LOGGER = logging.getLogger("ducocli")
LOGGER.propagate = False


class DebugLogOpenError(OSError):
    """
    *DebugLogOpenError The requested diagnostic file could not be opened.*

    args object - Diagnostic file error details accepted by OSError.
    """


def log_failure(stage: str, error: BaseException) -> None:
    """
    *log_failure Record stack locations without exception messages, source text or locals.*

    stage str - Operation being diagnosed.
    error BaseException - Exception raised by the operation.
    """
    if LOGGER.isEnabledFor(logging.DEBUG):
        frames = [
            f"{frame.f_globals.get('__name__')}.{frame.f_code.co_name}:{line}"
            for frame, line in walk_tb(error.__traceback__)
        ]
        LOGGER.debug("%s failed: %s at %s", stage, type(error).__name__, " > ".join(frames))


@contextmanager
def debug_session(enabled: bool):
    """
    *debug_session Attach a file handler for the duration of a debugging session.*

    enabled bool - Whether this session should append diagnostics to the log.
    """
    if not enabled:
        yield
        return
    try:
        handler = logging.FileHandler(Path.cwd() / "debug.log", encoding="utf-8")
    except OSError as exc:
        raise DebugLogOpenError from exc
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(process)d] %(name)s %(message)s"))
    previous_level = LOGGER.level
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.DEBUG)
    try:
        LOGGER.debug("Session started: DucoCLI %s Python %s %s", __version__,
                     platform.python_version(), platform.system())
        yield
    except Exception as exc:
        log_failure("Session", exc)
        raise
    finally:
        LOGGER.debug("Session ended")
        LOGGER.removeHandler(handler)
        LOGGER.setLevel(previous_level)
        handler.close()
