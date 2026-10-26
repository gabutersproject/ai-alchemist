"""Quiet logging. Prompts and file contents are never written to the log."""

import logging
import os


def configure_logging() -> None:
    """Send warnings to stderr. Debug requires PHANTOMOS_DEBUG."""
    level = logging.DEBUG if os.environ.get("PHANTOMOS_DEBUG") else logging.WARNING
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")
