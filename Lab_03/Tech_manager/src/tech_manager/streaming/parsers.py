"""Parsing stage: рядки CSV -> dict[str, str]."""

import csv
from collections.abc import Iterable, Iterator


def parse_csv_rows(lines: Iterable[str]) -> Iterator[dict[str, str]]:
    """Перший рядок - заголовок; далі по одному dict на кожний рядок."""
    reader = csv.DictReader(lines)
    yield from reader
