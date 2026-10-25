"""Thread and process based statistics calculations."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from threading import Lock, Thread
from collections.abc import Sequence

from equipment_manager.performance.analytics import (
    CostStatistics,
    build_statistics,
    validate_values,
)


PartialResult = tuple[int, float, float, float, float]


def split_values(
    values: Sequence[float],
    workers: int,
) -> list[list[float]]:
    """Split values into non-empty chunks."""
    if workers <= 0:
        raise ValueError("Workers must be positive.")

    chunk_size = max(1, len(values) // workers)
    chunks = [
        list(values[index : index + chunk_size])
        for index in range(0, len(values), chunk_size)
    ]

    return chunks


def calculate_partial_statistics(values: Sequence[float]) -> PartialResult:
    """Calculate partial moments for one chunk."""
    total = 0.0
    sum_of_squares = 0.0
    minimum = values[0]
    maximum = values[0]

    for value in values:
        total += value
        sum_of_squares += value * value

        if value < minimum:
            minimum = value

        if value > maximum:
            maximum = value

    return len(values), total, minimum, maximum, sum_of_squares


def merge_partial_statistics(
    partials: Sequence[PartialResult],
) -> CostStatistics:
    """Merge independent partial statistics."""
    count = sum(item[0] for item in partials)
    total = sum(item[1] for item in partials)
    minimum = min(item[2] for item in partials)
    maximum = max(item[3] for item in partials)
    sum_of_squares = sum(item[4] for item in partials)

    return build_statistics(
        count=count,
        total=total,
        minimum=minimum,
        maximum=maximum,
        sum_of_squares=sum_of_squares,
    )


def calculate_statistics_threads(
    values: Sequence[float],
    *,
    workers: int = 4,
) -> CostStatistics:
    """Calculate statistics using ThreadPoolExecutor."""
    validate_values(values)
    chunks = split_values(values, workers)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        partials = list(executor.map(calculate_partial_statistics, chunks))

    return merge_partial_statistics(partials)


def calculate_statistics_processes(
    values: Sequence[float],
    *,
    workers: int = 4,
) -> CostStatistics:
    """Calculate statistics using ProcessPoolExecutor."""
    validate_values(values)
    chunks = split_values(values, workers)

    with ProcessPoolExecutor(max_workers=workers) as executor:
        partials = list(executor.map(calculate_partial_statistics, chunks))

    return merge_partial_statistics(partials)


def count_values_with_threads(
    values: Sequence[float],
    *,
    workers: int = 4,
) -> int:
    """Count values with explicit Thread objects and synchronization."""
    validate_values(values)
    chunks = split_values(values, workers)
    lock = Lock()
    processed = 0

    def count_chunk(chunk: Sequence[float]) -> None:
        nonlocal processed

        local_count = len(chunk)

        with lock:
            processed += local_count

    threads = [
        Thread(target=count_chunk, args=(chunk,))
        for chunk in chunks
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    return processed