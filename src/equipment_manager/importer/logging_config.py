"""Logging setup: console, rotating application log."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

PACKAGE_LOGGER = "equipment_manager.importer"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_MARK = "_importer_handler"


def shutdown_logging() -> None:
    """Remove and close the handlers created by configure_logging()."""
    logger = logging.getLogger(PACKAGE_LOGGER)

    for handler in list(logger.handlers):
        if getattr(handler, _MARK, False):
            logger.removeHandler(handler)
            handler.close()


def configure_logging(
    level: str = "INFO",
    path: Path | None = None,
    *,
    max_bytes: int = 1_048_576,
    backup_count: int = 3,
) -> None:
    """Log to stderr and, optionally, to a rotating file."""
    shutdown_logging()
    logger = logging.getLogger(PACKAGE_LOGGER)
    logger.setLevel(level)
    formatter = logging.Formatter(LOG_FORMAT)

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]

    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            RotatingFileHandler(
                path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
        )

    for handler in handlers:
        handler.setFormatter(formatter)
        setattr(handler, _MARK, True)
        logger.addHandler(handler)
