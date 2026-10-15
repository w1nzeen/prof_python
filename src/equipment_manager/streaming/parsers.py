"""Stage 2: cleaning and parsing of text lines."""

import csv
from collections.abc import Iterable, Iterator


def clean_lines(lines: Iterable[str]) -> Iterator[str]:
    """Drop empty lines and line endings."""
    for line in lines:
        value = line.strip()

        if value:
            yield value


def parse_csv_rows(lines: Iterable[str]) -> Iterator[dict[str, str]]:
    """Turn CSV lines into dictionaries (the first line is the header)."""
    reader = csv.DictReader(lines)
    yield from reader
