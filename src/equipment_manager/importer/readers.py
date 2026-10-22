"""Streaming readers: one Importer per input format."""

import csv
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

from equipment_manager.importer.exceptions import DataImportError
from equipment_manager.importer.models import (
    EXTRA_FIELDS_KEY,
    FIELDS,
    RawRecord,
)

READ_ENCODING = "utf-8-sig"  # UTF-8, a BOM from Excel is skipped


class Importer(Protocol):
    """Anything that can stream raw records from a file."""

    def read(self, path: Path) -> Iterator[RawRecord]: ...


class CsvImporter:
    """Streaming CSV reader: rows are produced one at a time."""

    def read(self, path: Path) -> Iterator[RawRecord]:
        try:
            with path.open("r", encoding=READ_ENCODING, newline="") as file:
                reader = csv.DictReader(file)
                header = reader.fieldnames

                if header is None:
                    raise DataImportError(f"Input file is empty: {path}")

                missing = [name for name in FIELDS if name not in header]

                if missing:
                    raise DataImportError(
                        "Missing columns in header: " + ", ".join(missing)
                    )

                for row in reader:
                    data: dict[str, object] = {}

                    for key, value in row.items():
                        data[EXTRA_FIELDS_KEY if key is None else key] = value

                    yield RawRecord(reader.line_num, data)
        except (OSError, UnicodeDecodeError, csv.Error) as error:
            raise DataImportError(f"Cannot read CSV file {path}") from error


class JsonLinesImporter:
    """Streaming JSON Lines reader (one JSON object per line)."""

    def read(self, path: Path) -> Iterator[RawRecord]:
        try:
            with path.open("r", encoding=READ_ENCODING) as file:
                for line_number, line in enumerate(file, start=1):
                    if not line.strip():
                        continue

                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError as error:
                        raise DataImportError(
                            f"Invalid JSON at line {line_number}"
                        ) from error

                    yield RawRecord(line_number, _as_mapping(item))
        except (OSError, UnicodeDecodeError) as error:
            raise DataImportError(f"Cannot read file {path}") from error


class JsonImporter:
    """JSON array reader. The document is parsed as a whole."""

    def read(self, path: Path) -> Iterator[RawRecord]:
        try:
            with path.open("r", encoding=READ_ENCODING) as file:
                document = json.load(file)
        except json.JSONDecodeError as error:
            raise DataImportError(f"Invalid JSON document {path}") from error
        except (OSError, UnicodeDecodeError) as error:
            raise DataImportError(f"Cannot read file {path}") from error

        if not isinstance(document, list):
            raise DataImportError("JSON document must contain an array")

        for index, item in enumerate(document, start=1):
            yield RawRecord(index, _as_mapping(item))


def _as_mapping(item: object) -> dict[str, object]:
    if isinstance(item, dict):
        return {str(key): value for key, value in item.items()}

    return {}


IMPORTERS: dict[str, Importer] = {
    "csv": CsvImporter(),
    "json": JsonImporter(),
    "jsonl": JsonLinesImporter(),
}
EXTENSIONS: dict[str, str] = {
    ".csv": "csv",
    ".json": "json",
    ".jsonl": "jsonl",
    ".ndjson": "jsonl",
}


def detect_format(path: Path, declared: str = "auto") -> str:
    """Choose the format from the file extension when it is 'auto'."""
    if declared != "auto":
        return declared

    try:
        return EXTENSIONS[path.suffix.lower()]
    except KeyError as error:
        raise DataImportError(
            f"Cannot detect format by extension: {path.suffix!r}"
        ) from error


def get_importer(path: Path, declared: str = "auto") -> Importer:
    return IMPORTERS[detect_format(path, declared)]
