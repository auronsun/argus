"""Loguru-based logger with sensible defaults."""
from __future__ import annotations

import sys
from loguru import logger

from ..config import get_settings


def _configure() -> None:
    s = get_settings()
    logger.remove()
    logger.add(
        sys.stderr,
        level=s.argus_log_level,
        format="<green>{time:HH:mm:ss}</green> <level>{level:<7}</level> "
               "<cyan>{name}</cyan>:<cyan>{line}</cyan> {message}",
        backtrace=False,
        diagnose=False,
    )


_configure()

__all__ = ["logger"]
