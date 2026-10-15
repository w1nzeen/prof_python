"""Batch processing."""

from collections.abc import Iterable, Iterator
from itertools import islice

from equipment_manager.models import Device


def batched(
    devices: Iterable[Device],
    size: int,
) -> Iterator[list[Device]]:
    """Yield lists of `size` devices; only one batch is kept in memory."""
    if size < 1:
        raise ValueError("Batch size must be positive.")

    iterator = iter(devices)

    while True:
        batch = list(islice(iterator, size))

        if not batch:
            return

        yield batch


def dynamic_batches(
    devices: Iterable[Device],
    max_cost: float,
) -> Iterator[list[Device]]:
    """Dynamic batching: total cost of a batch does not exceed `max_cost`.

    A device that is more expensive than the limit gets its own batch.
    """
    batch: list[Device] = []
    batch_cost = 0.0

    for device in devices:
        if batch and batch_cost + device.cost > max_cost:
            yield batch
            batch = []
            batch_cost = 0.0

        batch.append(device)
        batch_cost += device.cost

    if batch:
        yield batch


def summarize_batches(
    batches: Iterable[list[Device]],
) -> Iterator[tuple[int, int, float]]:
    """For every batch yield (number, size, total cost)."""
    for number, batch in enumerate(batches, start=1):
        yield (number, len(batch), sum(device.cost for device in batch))
