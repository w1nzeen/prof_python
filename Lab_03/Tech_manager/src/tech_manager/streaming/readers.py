"""Source stage: streaming читання файлів по рядках."""

from collections.abc import Iterable, Iterator
from pathlib import Path


def read_lines(path: Path) -> Iterator[str]:
    """Читає файл по одному рядку, не завантажуючи його в пам'ять.

    File відкривається лише при першому next() і живе, поки iteration
    не завершено (або generator не закрито).
    """
    with path.open("r", encoding="utf-8", newline="") as file:
        yield from file


def clean_lines(lines: Iterable[str]) -> Iterator[str]:
    """Stage очищення: відкидає порожні рядки."""
    for line in lines:
        if line.strip():
            yield line
