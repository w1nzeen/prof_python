"""Lazy пошук із early termination."""

from collections.abc import Callable, Iterable
from itertools import islice

from tech_manager.streaming.records import TechRecord


def _close(iterator: object) -> None:
    close = getattr(iterator, "close", None)
    if callable(close):
        close()  # звільняє відкритий file, якщо споживання припинено достроково


def find_first(
    records: Iterable[TechRecord],
    predicate: Callable[[TechRecord], bool],
) -> TechRecord | None:
    """Повертає перший запис, що задовольняє умову; решта потоку не читається."""
    iterator = iter(records)
    try:
        for record in iterator:
            if predicate(record):
                return record
        return None
    finally:
        _close(iterator)


def find_by_inventory_number(
    records: Iterable[TechRecord], inventory_number: str
) -> TechRecord | None:
    return find_first(records, lambda r: r.inventory_number == inventory_number)


def take(records: Iterable[TechRecord], limit: int) -> list[TechRecord]:
    """Перші N записів (islice) із закриттям потоку."""
    iterator = iter(records)
    try:
        return list(islice(iterator, limit))
    finally:
        _close(iterator)
