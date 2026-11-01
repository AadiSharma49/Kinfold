"""Structured (JSON-lines) logging setup, so every request produces one
machine-parseable log line instead of whatever each library's default
formatter happens to do. See docs/security.md."""

from __future__ import annotations

import logging
import sys


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))  # message is already a JSON string

    root = logging.getLogger("kinfold_api")
    root.setLevel(logging.INFO)
    root.handlers = [handler]
    root.propagate = False
