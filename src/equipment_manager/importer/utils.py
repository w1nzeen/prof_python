"""Context managers: logged operation and atomic (transactional) writing."""

import logging
import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter
from typing import TextIO

from equipment_manager.importer.exceptions import DataExportError

logger = logging.getLogger(__name__)


@contextmanager
def logged_operation(operation: str) -> Iterator[None]:
    """Log start, finish and duration; log the traceback on failure."""
    logger.info("%s started", operation)
    start = perf_counter()

    try:
        yield
    except Exception:
        logger.exception("%s failed", operation)
        raise
    else:
        elapsed = perf_counter() - start
        logger.info("%s finished in %.6f s", operation, elapsed)


def temporary_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".tmp")


@contextmanager
def atomic_writer(path: Path, *, backup: bool = False) -> Iterator[TextIO]:
    """Write to a temporary file and replace `path` only on success.

    On any error the temporary file is removed and the previous output
    stays untouched. OSError is converted to DataExportError (chaining).
    """
    temporary = temporary_path(path)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        with temporary.open("w", encoding="utf-8") as file:
            yield file
            file.flush()
            os.fsync(file.fileno())

        if backup and path.exists():
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))

        temporary.replace(path)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise DataExportError(f"Cannot write {path}") from error
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
