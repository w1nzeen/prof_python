"""Streaming exporters with atomic output."""

import json
import textwrap
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from equipment_manager.importer.exceptions import DataExportError
from equipment_manager.importer.models import EquipmentRecord
from equipment_manager.importer.utils import atomic_writer


class Exporter(Protocol):
    """Anything that can write records to a file."""

    def write(self, records: Iterable[EquipmentRecord], path: Path) -> int: ...


class JsonExporter:
    """Streaming JSON array writer: records are never kept in memory."""

    def __init__(self, *, backup: bool = False) -> None:
        self.backup = backup

    def write(self, records: Iterable[EquipmentRecord], path: Path) -> int:
        count = 0

        with atomic_writer(path, backup=self.backup) as file:
            file.write("[\n")

            for record in records:
                if count:
                    file.write(",\n")

                try:
                    text = json.dumps(
                        record.to_dict(),
                        ensure_ascii=False,
                        indent=2,
                    )
                except TypeError as error:
                    raise DataExportError(
                        "Record is not JSON serializable"
                    ) from error

                file.write(textwrap.indent(text, "  "))
                count += 1

            file.write("\n]\n")

        return count


class JsonLinesExporter:
    """JSON Lines writer: one object per line, easy to stream."""

    def __init__(self, *, backup: bool = False) -> None:
        self.backup = backup

    def write(self, records: Iterable[EquipmentRecord], path: Path) -> int:
        count = 0

        with atomic_writer(path, backup=self.backup) as file:
            for record in records:
                file.write(json.dumps(record.to_dict(), ensure_ascii=False))
                file.write("\n")
                count += 1

        return count


EXPORT_EXTENSIONS: dict[str, str] = {
    ".json": "json",
    ".jsonl": "jsonl",
    ".ndjson": "jsonl",
}


def get_exporter(
    path: Path,
    declared: str = "auto",
    *,
    backup: bool = False,
) -> Exporter:
    """Choose the exporter by the declared format or the extension."""
    name = declared

    if name == "auto":
        try:
            name = EXPORT_EXTENSIONS[path.suffix.lower()]
        except KeyError as error:
            raise DataExportError(
                f"Cannot detect output format by extension: {path.suffix!r}"
            ) from error

    if name == "json":
        return JsonExporter(backup=backup)

    if name == "jsonl":
        return JsonLinesExporter(backup=backup)

    raise DataExportError(f"Unsupported output format: {name}")
