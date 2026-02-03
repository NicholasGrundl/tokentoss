"""Logging configuration for tokentoss."""

import logging
import sys

# Package-level logger
_package_logger = logging.getLogger("tokentoss")
_package_logger.addHandler(logging.NullHandler())  # Library convention

# Sentinel for our handler
_HANDLER_NAME = "_tokentoss_stream"


def enable_debug(level: int = logging.DEBUG) -> None:
    """Enable debug logging for tokentoss.

    Jupyter-friendly: outputs to stdout (not stderr) to avoid
    red-colored output in notebook cells.

    Can be called multiple times safely (won't duplicate handlers).
    """
    _package_logger.setLevel(level)

    # Don't add duplicate handlers
    for h in _package_logger.handlers:
        if getattr(h, "name", None) == _HANDLER_NAME:
            h.setLevel(level)
            return

    handler = logging.StreamHandler(sys.stdout)
    handler.name = _HANDLER_NAME
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("[%(name)s %(levelname)s] %(message)s"))
    _package_logger.addHandler(handler)


def disable_debug() -> None:
    """Disable debug logging and remove the tokentoss handler."""
    _package_logger.setLevel(logging.WARNING)
    _package_logger.handlers = [
        h for h in _package_logger.handlers if getattr(h, "name", None) != _HANDLER_NAME
    ]
