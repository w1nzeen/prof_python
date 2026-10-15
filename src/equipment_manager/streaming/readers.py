"""Stage 1: streaming reading of the source file."""

from collections.abc import Iterator
from pathlib import Path


def read_lines(path: Path) -> Iterator[str]:
    """Read a file line by line; the whole file is never loaded."""
    with path.open("r", encoding="utf-8", newline="") as file:
        yield from file
