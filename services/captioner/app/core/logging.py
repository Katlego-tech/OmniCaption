"""Structured stdlib logging configuration.

The eval harness reads stdout/stderr, so we keep logs single-line and prefixed
with a stable, greppable format. Call :func:`get_logger` from any module.
"""

from __future__ import annotations

import logging
import os
import sys

_CONFIGURED = False

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def _configure_root() -> None:
    """Configure the root logger exactly once (idempotent)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = os.environ.get("OMNICAPTION_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger.

    Args:
        name: Logger name, conventionally the calling module's ``__name__``.

    Returns:
        A :class:`logging.Logger` writing single-line records to stdout.
    """
    _configure_root()
    return logging.getLogger(name)
