from __future__ import annotations

import sys
from importlib.metadata import version

from loguru import logger

__version__ = version("jobpilot")


logger.disable("jobpilot")


def enable_logging(level: str | int = "INFO") -> None:
    logger.enable("jobpilot")
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
    )
