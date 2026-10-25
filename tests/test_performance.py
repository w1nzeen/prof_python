"""Tests for laboratory work 9 performance helpers."""

from __future__ import annotations

import math

import pytest

from equipment_manager.performance.analytics import (
    cached_statistics,
    calculate_statistics_numpy,
    calculate_statistics_sequential,
    clear_statistics_cache,
    generate_costs,
)
from equipment_manager.performance.parallel import (
    calculate_statistics_processes,
    calculate_statistics_threads,
    count_values_with_threads,
)
from equipment_manager.performance.profiling import (
    calculate_speedup,
    measure_memory,
    measure_performance,
)


def assert_statistics_equal(first, second) -> None:
    """Compare two statistics objects with float tolerance."""
    assert first.count == second.count
    assert first.total == pytest.approx(second.total)
    assert first.average == pytest.approx(second.average)
    assert first.minimum == pytest.approx(second.minimum)
    assert first.maximum == pytest.approx(second.maximum)
    assert first.variance == pytest.approx(second.variance)
    assert first.standard_deviation == pytest.approx(
        second.standard_deviation
    )


@pytest.fixture
def costs() -> list[float]:
    """Return a deterministic dataset for correctness tests."""
    return generate_costs(1_000)


def test_numpy_result_equals_sequential_result(costs: list[float]) -> None:
    sequential = calculate_statistics_sequential(costs)
    numpy_result = calculate_statistics_numpy(costs)

    assert_statistics_equal(sequential, numpy_result)


@pytest.mark.parametrize("workers", [1, 2, 4])
def test_thread_pool_result_equals_sequential_result(
    costs: list[float],
    workers: int,
) -> None:
    sequential = calculate_statistics_sequential(costs)
    threaded = calculate_statistics_threads(costs, workers=workers)

    assert_statistics_equal(sequential, threaded)


@pytest.mark.parametrize("workers", [1, 2])
def test_process_pool_result_equals_sequential_result(
    costs: list[float],
    workers: int,
) -> None:
    sequential = calculate_statistics_sequential(costs)
    processed = calculate_statistics_processes(costs, workers=workers)

    assert_statistics_equal(sequential, processed)


def test_explicit_threads_count_every_value(costs: list[float]) -> None:
    assert count_values_with_threads(costs, workers=4) == len(costs)


def test_cached_statistics_has_cache_hit(costs: list[float]) -> None:
    clear_statistics_cache()
    immutable_costs = tuple(costs)

    first = cached_statistics(immutable_costs)
    second = cached_statistics(immutable_costs)

    assert first == second
    assert cached_statistics.cache_info().hits == 1


def test_cache_invalidation_clears_cache(costs: list[float]) -> None:
    clear_statistics_cache()
    cached_statistics(tuple(costs))

    clear_statistics_cache()

    assert cached_statistics.cache_info().currsize == 0


def test_measure_performance_returns_positive_time(
    costs: list[float],
) -> None:
    result = measure_performance(
        calculate_statistics_sequential,
        costs,
        repeats=2,
    )

    assert len(result.runs) == 2
    assert result.mean_seconds > 0
    assert result.minimum_seconds > 0


def test_measure_memory_returns_non_negative_values(
    costs: list[float],
) -> None:
    result = measure_memory(
        calculate_statistics_sequential,
        costs,
    )

    assert result.current_bytes >= 0
    assert result.peak_bytes >= 0


def test_speedup_is_calculated_correctly() -> None:
    assert calculate_speedup(2.0, 0.5) == 4.0


@pytest.mark.parametrize(
    "values",
    [
        [],
        [100.0, math.inf],
        [100.0, math.nan],
    ],
)
def test_invalid_values_are_rejected(values: list[float]) -> None:
    with pytest.raises(ValueError):
        calculate_statistics_sequential(values)