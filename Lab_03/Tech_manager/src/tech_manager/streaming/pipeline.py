"""Складання lazy pipeline та streaming sink (export)."""

import csv
import logging
import math
from collections import Counter
from collections.abc import Iterable, Iterator
from itertools import chain
from pathlib import Path

from tech_manager.streaming.filters import (
    ValidationReport,
    filter_by_cost,
    filter_by_manufacturer,
    filter_by_type,
    validate_records,
)
from tech_manager.streaming.parsers import parse_csv_rows
from tech_manager.streaming.readers import clean_lines, read_lines
from tech_manager.streaming.records import CSV_FIELDS, TechRecord
from tech_manager.streaming.transformations import normalize_records

logger = logging.getLogger(__name__)


def _count_items(name: str, stream: Iterable, counts: Counter[str]) -> Iterator:
    counts[name] += 0
    for item in stream:
        counts[name] += 1
        yield item
    logger.debug("stage %s finished: %d items", name, counts[name])


def tap(name: str, stream: Iterable, counts: Counter[str] | None) -> Iterable:
    """Logging stage: рахує елементи, що пройшли через stage `name`."""
    return stream if counts is None else _count_items(name, stream, counts)


def read_rows(path: Path) -> Iterator[dict[str, str]]:
    """source -> read_lines -> clean_lines -> parse_csv_rows."""
    return parse_csv_rows(clean_lines(read_lines(path)))


def build_stream_from_rows(
    rows: Iterable[dict[str, str]],
    *,
    manufacturers: tuple[str, ...] = (),
    types: tuple[str, ...] = (),
    min_cost: float | None = None,
    max_cost: float | None = None,
    report: ValidationReport | None = None,
    counts: Counter[str] | None = None,
) -> Iterator[TechRecord]:
    """validate -> normalize -> filter. Нічого не читається до споживання."""
    stream: Iterable = tap("rows", rows, counts)
    stream = validate_records(stream, report)
    stream = tap("valid", stream, counts)
    stream = normalize_records(stream)
    if manufacturers:
        stream = filter_by_manufacturer(stream, *manufacturers)
    if types:
        stream = filter_by_type(stream, *types)
    if min_cost is not None or max_cost is not None:
        stream = filter_by_cost(
            stream,
            0.0 if min_cost is None else min_cost,
            math.inf if max_cost is None else max_cost,
        )
    return iter(tap("filtered", stream, counts))


def build_stream(path: Path, **options) -> Iterator[TechRecord]:
    """Pipeline для одного файлу."""
    return build_stream_from_rows(read_rows(path), **options)


def build_multi_file_stream(paths: Iterable[Path], **options) -> Iterator[TechRecord]:
    """Pipeline для декількох файлів (itertools.chain.from_iterable)."""
    rows = chain.from_iterable(read_rows(path) for path in paths)
    return build_stream_from_rows(rows, **options)


def export_csv(records: Iterable[TechRecord], path: Path) -> int:
    """Streaming sink: записує потік у новий CSV по одному рядку."""
    written = 0
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_FIELDS)
        for record in records:
            writer.writerow(record)
            written += 1
    return written
