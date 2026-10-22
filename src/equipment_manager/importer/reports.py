"""Separate error log (CSV) and export summary."""

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Self, TextIO

from equipment_manager.importer.exceptions import (
    DataExportError,
    RecordValidationError,
)
from equipment_manager.importer.utils import atomic_writer

ERROR_COLUMNS = ("line_number", "field", "message", "value")


class ErrorReport:
    """Class-based context manager that writes invalid records to CSV."""

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.count = 0
        self._file: TextIO | None = None
        self._writer: csv.DictWriter[str] | None = None

    def __enter__(self) -> Self:
        if self.path is None:
            return self

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._file = self.path.open("w", encoding="utf-8", newline="")
        except OSError as error:
            raise DataExportError(f"Cannot open error log {self.path}") from error

        self._writer = csv.DictWriter(self._file, fieldnames=ERROR_COLUMNS)
        self._writer.writeheader()

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None

    def record(self, error: RecordValidationError) -> None:
        self.count += 1

        if self._writer is not None:
            self._writer.writerow(
                {
                    "line_number": str(error.line_number or ""),
                    "field": error.field or "",
                    "message": str(error),
                    "value": error.value or "",
                }
            )


@dataclass(frozen=True)
class SummaryTarget:
    path: Path
    backup: bool = False


def write_summary(summary: dict[str, object], target: SummaryTarget) -> None:
    """Atomically write the export summary report as JSON."""
    with atomic_writer(target.path, backup=target.backup) as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)
        file.write("\n")
