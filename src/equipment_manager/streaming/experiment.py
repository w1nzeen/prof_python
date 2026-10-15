"""Test data generation and the eager vs lazy experiment."""

import csv
import random
import tempfile
import tracemalloc
from collections.abc import Callable, Iterator
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, TypeVar

from equipment_manager.data import DEVICE_TYPES, MANUFACTURERS
from equipment_manager.models import Device
from equipment_manager.streaming.analytics import (
    StreamStatistics,
    calculate_statistics,
)
from equipment_manager.streaming.filters import (
    filter_items,
    find_first,
    validate_devices,
)
from equipment_manager.streaming.iterators import InventoryNumberRange
from equipment_manager.streaming.parsers import clean_lines, parse_csv_rows
from equipment_manager.streaming.pipeline import build_pipeline
from equipment_manager.streaming.readers import read_lines
from equipment_manager.streaming.transformations import normalize_devices

T = TypeVar("T")

HEADER = ["inventory_number", "type", "manufacturer", "model", "cost"]
DEFAULT_SIZES: tuple[int, ...] = (10_000, 100_000, 500_000)
EARLY_TERMINATION_SIZE = 1_000_000
MEGABYTE = 1024 * 1024


@dataclass(frozen=True)
class ExperimentRow:
    records: int
    eager_time: float
    lazy_time: float
    eager_peak: int
    lazy_peak: int
    eager_first: float
    lazy_first: float


@dataclass(frozen=True)
class EarlyTerminationResult:
    records: int
    lazy_time: float
    eager_time: float
    lazy_found: Device | None
    eager_matches: int


def generate_csv(
    path: Path,
    count: int,
    seed: int = 42,
    invalid_ratio: float = 0.01,
) -> None:
    """Write `count` records; about `invalid_ratio` of them are broken."""
    rng = random.Random(seed)

    def rows() -> Iterator[list[object]]:
        for number in InventoryNumberRange("PC", 1, count + 1):
            cost: object = (
                "error"
                if rng.random() < invalid_ratio
                else round(rng.uniform(300, 80000), 2)
            )

            yield [
                number,
                rng.choice(DEVICE_TYPES),
                rng.choice(MANUFACTURERS),
                f"Model-{rng.randint(1, 99)}",
                cost,
            ]

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(HEADER)
        writer.writerows(rows())


def eager_load(path: Path) -> list[Device]:
    """Eager variant: every stage materializes its own list."""
    lines = list(clean_lines(read_lines(path)))
    rows = list(parse_csv_rows(lines))
    valid = list(validate_devices(rows))

    return list(normalize_devices(valid))


def eager_run(path: Path) -> StreamStatistics:
    return calculate_statistics(eager_load(path))


def lazy_run(path: Path) -> StreamStatistics:
    return calculate_statistics(build_pipeline(path))


def measure_time(function: Callable[..., T], *args: Any) -> tuple[T, float]:
    start = perf_counter()
    result = function(*args)

    return result, perf_counter() - start


def measure_peak_memory(
    function: Callable[..., T],
    *args: Any,
) -> tuple[T, int]:
    """Peak memory in bytes. The result must be fully consumed inside."""
    tracemalloc.start()

    try:
        result = function(*args)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    return result, peak


def eager_first_result_time(path: Path) -> float:
    """Eager: the first record is available only after full loading."""
    start = perf_counter()
    devices = eager_load(path)
    _ = devices[0]

    return perf_counter() - start


def lazy_first_result_time(path: Path) -> float:
    start = perf_counter()
    pipeline = build_pipeline(path)

    with closing(pipeline):
        next(pipeline, None)

    return perf_counter() - start


def run_experiment(
    sizes: tuple[int, ...] = DEFAULT_SIZES,
) -> list[ExperimentRow]:
    """Compare eager and lazy variants on files of different size.

    Time and memory are measured in separate runs, because tracemalloc
    slows the program down noticeably.
    """
    rows: list[ExperimentRow] = []

    with tempfile.TemporaryDirectory() as directory:
        for size in sizes:
            path = Path(directory) / f"devices_{size}.csv"
            generate_csv(path, size)

            eager_stats, eager_time = measure_time(eager_run, path)
            lazy_stats, lazy_time = measure_time(lazy_run, path)

            if eager_stats != lazy_stats:
                raise RuntimeError("Eager and lazy results differ.")

            _, eager_peak = measure_peak_memory(eager_run, path)
            _, lazy_peak = measure_peak_memory(lazy_run, path)

            rows.append(
                ExperimentRow(
                    records=size,
                    eager_time=eager_time,
                    lazy_time=lazy_time,
                    eager_peak=eager_peak,
                    lazy_peak=lazy_peak,
                    eager_first=eager_first_result_time(path),
                    lazy_first=lazy_first_result_time(path),
                )
            )

    return rows


def is_expensive_server(device: Device) -> bool:
    return device.device_type == "Server" and device.cost >= 75000


def run_early_termination(
    size: int = EARLY_TERMINATION_SIZE,
) -> EarlyTerminationResult:
    """Find the first matching record: lazy search vs full filtered list."""
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "devices.csv"
        generate_csv(path, size)

        def lazy_search() -> Device | None:
            pipeline = build_pipeline(path)

            with closing(pipeline):
                return find_first(pipeline, is_expensive_server)

        def eager_search() -> list[Device]:
            return list(filter_items(build_pipeline(path), is_expensive_server))

        found, lazy_time = measure_time(lazy_search)
        matches, eager_time = measure_time(eager_search)

    return EarlyTerminationResult(
        records=size,
        lazy_time=lazy_time,
        eager_time=eager_time,
        lazy_found=found,
        eager_matches=len(matches),
    )


def print_experiment(rows: list[ExperimentRow]) -> None:
    print(
        f"{'Records':>9}{'Eager, s':>11}{'Lazy, s':>10}"
        f"{'Eager peak, MB':>16}{'Lazy peak, MB':>15}"
        f"{'Eager 1st, s':>14}{'Lazy 1st, s':>13}"
    )

    for row in rows:
        print(
            f"{row.records:>9,}{row.eager_time:>11.3f}{row.lazy_time:>10.3f}"
            f"{row.eager_peak / MEGABYTE:>16.2f}"
            f"{row.lazy_peak / MEGABYTE:>15.2f}"
            f"{row.eager_first:>14.3f}{row.lazy_first:>13.6f}"
        )


def print_early_termination(result: EarlyTerminationResult) -> None:
    print(
        f"Find the first expensive server in {result.records:,} records:"
    )
    print(f"  lazy  (find_first):      {result.lazy_time:.6f} s")
    print(
        f"  eager (full list, {result.eager_matches:,} matches): "
        f"{result.eager_time:.3f} s"
    )

    if result.lazy_found is not None:
        print("  found:", result.lazy_found.inventory_number)
