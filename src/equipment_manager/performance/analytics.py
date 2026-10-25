"""Sequential, NumPy and cached equipment cost statistics."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from functools import lru_cache
from collections.abc import Sequence

import numpy as np


@dataclass(frozen=True)
class CostStatistics:
    """Statistics calculated from equipment costs."""

    count: int
    total: float
    average: float
    minimum: float
    maximum: float
    variance: float
    standard_deviation: float


def validate_values(values: Sequence[float]) -> None:
    """Validate an input dataset before calculations."""
    if not values:
        raise ValueError("At least one value is required.")

    if not all(math.isfinite(value) for value in values):
        raise ValueError("Every value must be finite.")


def build_statistics(
    count: int,
    total: float,
    minimum: float,
    maximum: float,
    sum_of_squares: float,
) -> CostStatistics:
    """Build statistics from partial sums."""
    if count <= 0:
        raise ValueError("Count must be positive.")

    average = total / count
    variance = max(sum_of_squares / count - average**2, 0.0)

    return CostStatistics(
        count=count,
        total=total,
        average=average,
        minimum=minimum,
        maximum=maximum,
        variance=variance,
        standard_deviation=math.sqrt(variance),
    )


def calculate_statistics_sequential(values: Sequence[float]) -> CostStatistics:
    """Baseline Python-loop implementation."""
    validate_values(values)

    total = 0.0
    minimum = values[0]
    maximum = values[0]
    sum_of_squares = 0.0

    for value in values:
        total += value
        sum_of_squares += value * value

        if value < minimum:
            minimum = value

        if value > maximum:
            maximum = value

    return build_statistics(
        count=len(values),
        total=total,
        minimum=minimum,
        maximum=maximum,
        sum_of_squares=sum_of_squares,
    )


def calculate_statistics_numpy(values: Sequence[float]) -> CostStatistics:
    """Vectorized NumPy implementation."""
    validate_values(values)

    array = np.asarray(values, dtype=np.float64)

    return CostStatistics(
        count=int(array.size),
        total=float(np.sum(array)),
        average=float(np.mean(array)),
        minimum=float(np.min(array)),
        maximum=float(np.max(array)),
        variance=float(np.var(array)),
        standard_deviation=float(np.std(array)),
    )


@lru_cache(maxsize=128)
def cached_statistics(values: tuple[float, ...]) -> CostStatistics:
    """Return cached sequential statistics for an immutable dataset."""
    return calculate_statistics_sequential(values)


def clear_statistics_cache() -> None:
    """Invalidate cached statistics after the source data changes."""
    cached_statistics.cache_clear()


def generate_costs(
    size: int,
    *,
    seed: int = 42,
    minimum: float = 500.0,
    maximum: float = 150_000.0,
) -> list[float]:
    """Generate deterministic equipment costs for benchmarks."""
    if size <= 0:
        raise ValueError("Size must be positive.")

    if minimum < 0 or maximum <= minimum:
        raise ValueError("Invalid cost range.")

    generator = random.Random(seed)

    return [
        round(generator.uniform(minimum, maximum), 2)
        for _ in range(size)
    ]