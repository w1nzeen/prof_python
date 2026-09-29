"""Batch processing."""

from collections.abc import Iterable, Iterator
from itertools import islice

from tech_manager.streaming.records import TechRecord


def batched(iterable: Iterable[TechRecord], size: int) -> Iterator[list[TechRecord]]:
    """Batches фіксованого розміру; в пам'яті лише поточний batch."""
    if size < 1:
        raise ValueError("size must be >= 1")  # помилка одразу, не при next()
    return _batched(iterable, size)


def _batched(iterable: Iterable[TechRecord], size: int) -> Iterator[list[TechRecord]]:
    iterator = iter(iterable)
    while True:
        batch = list(islice(iterator, size))
        if not batch:
            return
        yield batch


def batched_by_cost(
    records: Iterable[TechRecord], max_total: float
) -> Iterator[list[TechRecord]]:
    """Dynamic batching: batch закривається, коли сума вартості перевищила б ліміт."""
    if max_total <= 0:
        raise ValueError("max_total must be positive")
    return _batched_by_cost(records, max_total)


def _batched_by_cost(
    records: Iterable[TechRecord], max_total: float
) -> Iterator[list[TechRecord]]:
    batch: list[TechRecord] = []
    total = 0.0
    for record in records:
        if batch and total + record.cost > max_total:
            yield batch
            batch, total = [], 0.0
        batch.append(record)
        total += record.cost
    if batch:
        yield batch


def summarize_batches(
    batches: Iterable[list[TechRecord]],
) -> Iterator[tuple[int, int, float]]:
    """Для кожного batch: (номер, кількість, сумарна вартість)."""
    for index, batch in enumerate(batches, start=1):
        yield index, len(batch), round(sum(record.cost for record in batch), 2)
