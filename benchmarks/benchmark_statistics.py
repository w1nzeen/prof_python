"""Run laboratory work 9 benchmarks for equipment cost statistics."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

from equipment_manager.performance.analytics import (
    CostStatistics,
    cached_statistics,
    calculate_statistics_numpy,
    calculate_statistics_sequential,
    clear_statistics_cache,
    generate_costs,
)
from equipment_manager.performance.parallel import (
    calculate_statistics_processes,
    calculate_statistics_threads,
)
from equipment_manager.performance.profiling import (
    calculate_speedup,
    measure_memory,
    measure_performance,
    profile_function,
)


DATASET_SIZES = (10_000, 100_000, 1_000_000)
WORKER_COUNTS = (1, 2, 4)
REPEATS = 3
RESULTS_DIRECTORY = Path(__file__).parent / "results"


@dataclass(frozen=True)
class BenchmarkRow:
    """One row of benchmark output."""

    dataset_size: int
    method: str
    workers: str
    mean_seconds: float
    peak_memory_megabytes: float
    speedup: float


def statistics_are_equal(
    first: CostStatistics,
    second: CostStatistics,
) -> bool:
    """Compare floating-point statistics with a reasonable tolerance."""
    return (
        first.count == second.count
        and math.isclose(first.total, second.total, rel_tol=1e-9)
        and math.isclose(first.average, second.average, rel_tol=1e-9)
        and math.isclose(first.minimum, second.minimum, rel_tol=1e-9)
        and math.isclose(first.maximum, second.maximum, rel_tol=1e-9)
        and math.isclose(first.variance, second.variance, rel_tol=1e-9)
        and math.isclose(
            first.standard_deviation,
            second.standard_deviation,
            rel_tol=1e-9,
        )
    )


def add_row(
    rows: list[BenchmarkRow],
    *,
    dataset_size: int,
    method: str,
    workers: str,
    baseline_seconds: float,
    function,
    values,
) -> None:
    """Measure one implementation and append a benchmark row."""
    benchmark = measure_performance(
        function,
        values,
        repeats=REPEATS,
    )
    memory = measure_memory(function, values)

    rows.append(
        BenchmarkRow(
            dataset_size=dataset_size,
            method=method,
            workers=workers,
            mean_seconds=benchmark.mean_seconds,
            peak_memory_megabytes=memory.peak_megabytes,
            speedup=calculate_speedup(
                baseline_seconds,
                benchmark.mean_seconds,
            ),
        )
    )


def write_csv(rows: list[BenchmarkRow]) -> Path:
    """Write benchmark rows to CSV."""
    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIRECTORY / "benchmark_results.csv"

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "dataset_size",
                "method",
                "workers",
                "mean_seconds",
                "peak_memory_megabytes",
                "speedup",
            ],
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    "dataset_size": row.dataset_size,
                    "method": row.method,
                    "workers": row.workers,
                    "mean_seconds": f"{row.mean_seconds:.8f}",
                    "peak_memory_megabytes": (
                        f"{row.peak_memory_megabytes:.4f}"
                    ),
                    "speedup": f"{row.speedup:.4f}",
                }
            )

    return path


def print_rows(rows: list[BenchmarkRow]) -> None:
    """Print benchmark results in a readable table."""
    print(
        f"{'Dataset':>10} {'Method':<18} {'Workers':>7} "
        f"{'Mean, s':>12} {'Peak, MB':>12} {'Speedup':>10}"
    )

    for row in rows:
        print(
            f"{row.dataset_size:>10} {row.method:<18} "
            f"{row.workers:>7} {row.mean_seconds:>12.6f} "
            f"{row.peak_memory_megabytes:>12.3f} "
            f"{row.speedup:>9.2f}x"
        )


def benchmark_dataset(size: int) -> list[BenchmarkRow]:
    """Benchmark every required implementation for one dataset size."""
    values = generate_costs(size)
    baseline = calculate_statistics_sequential(values)
    rows: list[BenchmarkRow] = []

    baseline_benchmark = measure_performance(
        calculate_statistics_sequential,
        values,
        repeats=REPEATS,
    )
    baseline_memory = measure_memory(
        calculate_statistics_sequential,
        values,
    )

    rows.append(
        BenchmarkRow(
            dataset_size=size,
            method="Sequential",
            workers="1",
            mean_seconds=baseline_benchmark.mean_seconds,
            peak_memory_megabytes=baseline_memory.peak_megabytes,
            speedup=1.0,
        )
    )

    for workers in WORKER_COUNTS:
        threaded = calculate_statistics_threads(
            values,
            workers=workers,
        )
        processed = calculate_statistics_processes(
            values,
            workers=workers,
        )

        assert statistics_are_equal(baseline, threaded)
        assert statistics_are_equal(baseline, processed)

        add_row(
            rows,
            dataset_size=size,
            method="ThreadPool",
            workers=str(workers),
            baseline_seconds=baseline_benchmark.mean_seconds,
            function=lambda items: calculate_statistics_threads(
                items,
                workers=workers,
            ),
            values=values,
        )
        add_row(
            rows,
            dataset_size=size,
            method="ProcessPool",
            workers=str(workers),
            baseline_seconds=baseline_benchmark.mean_seconds,
            function=lambda items: calculate_statistics_processes(
                items,
                workers=workers,
            ),
            values=values,
        )

    numpy_statistics = calculate_statistics_numpy(values)
    assert statistics_are_equal(baseline, numpy_statistics)

    add_row(
        rows,
        dataset_size=size,
        method="NumPy",
        workers="-",
        baseline_seconds=baseline_benchmark.mean_seconds,
        function=calculate_statistics_numpy,
        values=values,
    )

    clear_statistics_cache()
    immutable_values = tuple(values)
    cached_statistics(immutable_values)

    cached_benchmark = measure_performance(
        cached_statistics,
        immutable_values,
        repeats=REPEATS,
    )
    cached_memory = measure_memory(
        cached_statistics,
        immutable_values,
    )

    rows.append(
        BenchmarkRow(
            dataset_size=size,
            method="Cached warm",
            workers="-",
            mean_seconds=cached_benchmark.mean_seconds,
            peak_memory_megabytes=cached_memory.peak_megabytes,
            speedup=calculate_speedup(
                baseline_benchmark.mean_seconds,
                cached_benchmark.mean_seconds,
            ),
        )
    )

    return rows


def save_profile() -> Path:
    """Save cProfile output for the largest dataset."""
    values = generate_costs(DATASET_SIZES[-1])
    profile = profile_function(
        calculate_statistics_sequential,
        values,
    )

    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIRECTORY / "cprofile_statistics.txt"
    path.write_text(profile, encoding="utf-8")

    return path


def main() -> None:
    """Run all benchmarks and save their results."""
    all_rows: list[BenchmarkRow] = []

    for size in DATASET_SIZES:
        print(f"Benchmarking dataset with {size:,} values...")
        all_rows.extend(benchmark_dataset(size))

    csv_path = write_csv(all_rows)
    profile_path = save_profile()
    print_rows(all_rows)
    print(f"\nCSV results: {csv_path}")
    print(f"cProfile results: {profile_path}")


if __name__ == "__main__":
    main()