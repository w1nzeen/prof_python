"""Command line entry point of the reliable importer."""

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from equipment_manager.importer.config import load_and_validate
from equipment_manager.importer.exceptions import ApplicationError
from equipment_manager.importer.logging_config import (
    configure_logging,
    shutdown_logging,
)
from equipment_manager.importer.services import run_import

logger = logging.getLogger(__name__)

EXIT_APPLICATION_ERROR = 1
EXIT_UNEXPECTED_ERROR = 2


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="equipment-importer")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="path to the YAML configuration (default: config.yaml)",
    )
    args = parser.parse_args(argv)

    # errors that happen before the configuration is read must be visible
    configure_logging("INFO")

    try:
        config = load_and_validate(args.config)
        configure_logging(
            config.logging.level,
            config.logging.path,
            max_bytes=config.logging.max_bytes,
            backup_count=config.logging.backup_count,
        )
        run_import(config)
    except ApplicationError as error:
        logger.error("Application error: %s", error)
        shutdown_logging()
        raise SystemExit(EXIT_APPLICATION_ERROR) from error
    except Exception as error:
        logger.exception("Unexpected error")
        shutdown_logging()
        raise SystemExit(EXIT_UNEXPECTED_ERROR) from error

    shutdown_logging()


if __name__ == "__main__":
    main()
