"""Generator functions: yield, yield from, нескінченні та рекурсивні генератори."""

from collections.abc import Iterable, Iterator
from itertools import count
from typing import Any


def even_numbers(limit: int) -> Iterator[int]:
    """Парні числа менші за limit (yield)."""
    for number in range(limit):
        if number % 2 == 0:
            yield number


def natural_numbers() -> Iterator[int]:
    """Нескінченний generator: 1, 2, 3, ... Споживати лише через islice."""
    value = 1
    while True:
        yield value
        value += 1


def inventory_numbers(start: int = 1, width: int = 6) -> Iterator[str]:
    """Нескінченний потік інвентарних номерів (yield from + itertools.count)."""
    yield from (f"{number:0{width}d}" for number in count(start))


def flatten(values: Iterable[Any]) -> Iterator[Any]:
    """Рекурсивний generator із yield from: розгортає вкладені списки."""
    for value in values:
        if isinstance(value, list):
            yield from flatten(value)
        else:
            yield value


def demo_yield_states() -> Iterator[int]:
    """Показує, що yield призупиняє функцію та зберігає стан."""
    print("  [demo] Start")
    yield 1
    print("  [demo] Continue")
    yield 2
    print("  [demo] Finish")
