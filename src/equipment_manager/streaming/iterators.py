"""Iterator protocol examples: iterable, iterator and generators."""

from collections.abc import Iterable, Iterator
from itertools import count, islice
from typing import Any, Self


class InventoryNumberIterator:
    """Iterator: keeps the current state and implements __next__()."""

    def __init__(self, prefix: str, start: int, stop: int) -> None:
        self.prefix = prefix
        self.current = start
        self.stop = stop

    def __iter__(self) -> Self:
        return self

    def __next__(self) -> str:
        if self.current >= self.stop:
            raise StopIteration

        value = f"{self.prefix}-{self.current:06d}"
        self.current += 1

        return value


class InventoryNumberRange:
    """Iterable: every iter() call creates a new independent iterator."""

    def __init__(self, prefix: str, start: int, stop: int) -> None:
        self.prefix = prefix
        self.start = start
        self.stop = stop

    def __iter__(self) -> InventoryNumberIterator:
        return InventoryNumberIterator(self.prefix, self.start, self.stop)


def inventory_numbers(prefix: str = "PC", start: int = 1) -> Iterator[str]:
    """Infinite generator: must always be limited, for example by islice."""
    for number in count(start):
        yield f"{prefix}-{number:06d}"


def take(iterable: Iterable[Any], size: int) -> list[Any]:
    """Take the first `size` items without consuming the whole stream."""
    return list(islice(iterable, size))


def flatten(values: Iterable[Any]) -> Iterator[Any]:
    """Recursive generator with yield from."""
    for value in values:
        if isinstance(value, list):
            yield from flatten(value)
        else:
            yield value
