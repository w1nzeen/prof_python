"""Експеримент: eager vs lazy (час, peak memory, time to first result).

Запуск: python -m tech_manager.streaming.experiment
"""

import argparse
import tempfile
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from tech_manager.streaming.analytics import StreamStatistics, calculate_statistics
from tech_manager.streaming.datagen import generate_test_file
from tech_manager.streaming.eager import eager_filtered, eager_find_first, eager_pipeline
from tech_manager.streaming.pipeline import build_stream
from tech_manager.streaming.search import find_first

SIZES: tuple[int, ...] = (10_000, 100_000, 500_000)
EARLY_TERMINATION_SIZE = 1_000_000
MIN_COST = 1500.0


def lazy_pipeline(path: Path, min_cost: float | None = None) -> StreamStatistics:
    return calculate_statistics(build_stream(path, min_cost=min_cost))


def time_call(func: Callable[..., Any], *args: Any) -> tuple[Any, float]:
    start = perf_counter()
    result = func(*args)
    return result, perf_counter() - start


def peak_memory_of(func: Callable[..., Any], *args: Any) -> tuple[Any, int]:
    """Peak memory (байти). Generator треба споживати всередині func."""
    tracemalloc.start()
    try:
        result = func(*args)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, peak


def lazy_time_to_first(path: Path, min_cost: float) -> float:
    start = perf_counter()
    stream = build_stream(path, min_cost=min_cost)
    next(stream, None)
    elapsed = perf_counter() - start
    stream.close()
    return elapsed


def eager_time_to_first(path: Path, min_cost: float) -> float:
    start = perf_counter()
    filtered = eager_filtered(path, min_cost)
    _ = filtered[0] if filtered else None
    return perf_counter() - start


@dataclass(frozen=True)
class ExperimentRow:
    size: int
    eager_time: float
    lazy_time: float
    eager_peak: int
    lazy_peak: int
    eager_first: float
    lazy_first: float
    same_result: bool


def run_size(path: Path, size: int) -> ExperimentRow:
    generate_test_file(path, size)
    eager_stats, eager_time = time_call(eager_pipeline, path, MIN_COST)
    lazy_stats, lazy_time = time_call(lazy_pipeline, path, MIN_COST)
    _, eager_peak = peak_memory_of(eager_pipeline, path, MIN_COST)
    _, lazy_peak = peak_memory_of(lazy_pipeline, path, MIN_COST)
    return ExperimentRow(
        size=size,
        eager_time=eager_time,
        lazy_time=lazy_time,
        eager_peak=eager_peak,
        lazy_peak=lazy_peak,
        eager_first=eager_time_to_first(path, MIN_COST),
        lazy_first=lazy_time_to_first(path, MIN_COST),
        same_result=eager_stats == lazy_stats,
    )


def early_termination(path: Path, size: int) -> dict[str, float | int]:
    """Пошук першого запису з cost >= 2990 у файлі на `size` records."""
    generate_test_file(path, size)

    def predicate(record) -> bool:
        return record.cost >= 2990.0

    from collections import Counter

    counts: Counter[str] = Counter()
    start = perf_counter()
    lazy_found = find_first(build_stream(path, counts=counts), predicate)
    lazy_time = perf_counter() - start

    start = perf_counter()
    eager_found = eager_find_first(path, predicate)
    eager_time = perf_counter() - start
    return {
        "size": size,
        "lazy_time": lazy_time,
        "eager_time": eager_time,
        "lazy_rows_read": counts["rows"],
        "same_record": lazy_found == eager_found,
    }


def list_vs_generator_memory(n: int = 1_000_000) -> dict[str, int]:
    """Peak memory: sum(list comprehension) проти sum(generator expression)."""
    _, list_peak = peak_memory_of(lambda: sum([x * x for x in range(n)]))
    _, gen_peak = peak_memory_of(lambda: sum(x * x for x in range(n)))
    return {"n": n, "list_peak": list_peak, "generator_peak": gen_peak}


def mib(value: int) -> str:
    return f"{value / 1024 / 1024:.2f} MiB"


def format_tables(rows: list[ExperimentRow]) -> str:
    lines = [
        "Elapsed time та time to first result (сек):",
        f"{'Records':>9} | {'Eager time':>11} | {'Lazy time':>10} | "
        f"{'Eager 1st':>10} | {'Lazy 1st':>10}",
        "-" * 62,
    ]
    for r in rows:
        lines.append(
            f"{r.size:>9,} | {r.eager_time:>11.3f} | {r.lazy_time:>10.3f} | "
            f"{r.eager_first:>10.3f} | {r.lazy_first:>10.5f}"
        )
    lines += [
        "",
        "Peak memory (tracemalloc):",
        f"{'Records':>9} | {'Eager peak':>12} | {'Lazy peak':>12} | {'Ratio':>8}",
        "-" * 50,
    ]
    for r in rows:
        lines.append(
            f"{r.size:>9,} | {mib(r.eager_peak):>12} | {mib(r.lazy_peak):>12} | "
            f"{r.eager_peak / max(r.lazy_peak, 1):>7.0f}x"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Eager vs lazy experiment")
    parser.add_argument("--sizes", type=int, nargs="+", default=list(SIZES))
    parser.add_argument("--early", type=int, default=EARLY_TERMINATION_SIZE)
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "large.csv"
        rows = []
        for size in args.sizes:
            print(f"Розмір {size:,}...", flush=True)
            rows.append(run_size(path, size))

        print()
        print(format_tables(rows))
        print("\nРезультати eager і lazy однакові:", all(r.same_result for r in rows))

        print(f"\nEarly termination ({args.early:,} records, перший cost >= 2990):")
        result = early_termination(path, args.early)
        print(f"  lazy : {result['lazy_time'] * 1000:10.3f} ms, "
              f"прочитано рядків: {result['lazy_rows_read']:,}")
        print(f"  eager: {result['eager_time'] * 1000:10.3f} ms, "
              f"прочитано рядків: {result['size']:,}")
        print("  однаковий запис:", result["same_record"])

    memory = list_vs_generator_memory()
    print(f"\nsum() для {memory['n']:,} елементів, peak memory:")
    print(f"  list comprehension  : {mib(memory['list_peak'])}")
    print(f"  generator expression: {memory['generator_peak'] / 1024:.2f} KiB")


if __name__ == "__main__":
    main()
