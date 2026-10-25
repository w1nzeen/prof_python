"""Benchmarking, CPU profiling and memory measurement helpers."""

from __future__ import annotations

import cProfile
import io
import pstats
import statistics
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from timeit import Timer
from typing import ParamSpec, TypeVar


Parameters = ParamSpec("Parameters")
Result = TypeVar("Result")


@dataclass(frozen=True)
class BenchmarkResult:
    """Results of repeated execution-time measurements."""

    runs: tuple[float, ...]
    mean_seconds: float
    minimum_seconds: float
    maximum_seconds: float


@dataclass(frozen=True)
class MemoryResult:
    """Current and peak traced memory consumption."""

    current_bytes: int
    peak_bytes: int

    @property
    def peak_megabytes(self) -> float:
        """Return peak memory in megabytes."""
        return self.peak_bytes / 1024 / 1024


def measure_performance(
    function: Callable[Parameters, Result],
    *args: Parameters.args,
    repeats: int = 5,
    **kwargs: Parameters.kwargs,
) -> BenchmarkResult:
    """Measure a function with perf_counter."""
    if repeats <= 0:
        raise ValueError("Repeats must be positive.")

    runs: list[float] = []

    for _ in range(repeats):
        started = perf_counter()
        function(*args, **kwargs)
        runs.append(perf_counter() - started)

    return BenchmarkResult(
        runs=tuple(runs),
        mean_seconds=statistics.fmean(runs),
        minimum_seconds=min(runs),
        maximum_seconds=max(runs),
    )


def measure_with_timeit(
    function: Callable[Parameters, Result],
    *args: Parameters.args,
    number: int = 5,
    **kwargs: Parameters.kwargs,
) -> float:
    """Measure a function with timeit."""
    if number <= 0:
        raise ValueError("Number must be positive.")

    timer = Timer(lambda: function(*args, **kwargs))

    return timer.timeit(number=number) / number


def profile_function(
    function: Callable[Parameters, Result],
    *args: Parameters.args,
    **kwargs: Parameters.kwargs,
) -> str:
    """Return cumulative cProfile statistics as text."""
    profiler = cProfile.Profile()
    profiler.enable()

    try:
        function(*args, **kwargs)
    finally:
        profiler.disable()

    stream = io.StringIO()
    statistics_report = pstats.Stats(profiler, stream=stream)
    statistics_report.sort_stats("cumulative")
    statistics_report.print_stats(20)

    return stream.getvalue()


def measure_memory(
    function: Callable[Parameters, Result],
    *args: Parameters.args,
    **kwargs: Parameters.kwargs,
) -> MemoryResult:
    """Measure Python allocations with tracemalloc."""
    tracemalloc.start()

    try:
        function(*args, **kwargs)
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    return MemoryResult(
        current_bytes=current,
        peak_bytes=peak,
    )


def calculate_speedup(
    baseline_seconds: float,
    optimized_seconds: float,
) -> float:
    """Calculate speedup relative to the baseline implementation."""
    if baseline_seconds <= 0 or optimized_seconds <= 0:
        raise ValueError("Execution times must be positive.")

    return baseline_seconds / optimized_seconds