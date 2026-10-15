"""Console demonstration of laboratory work 3."""

import sys
from collections.abc import Iterable
from contextlib import closing
from itertools import islice
from pathlib import Path

from equipment_manager.models import Device
from equipment_manager.streaming import analytics, batches
from equipment_manager.streaming.filters import (
    ValidationStats,
    find_by_inventory_number,
)
from equipment_manager.streaming.iterators import (
    InventoryNumberRange,
    flatten,
    inventory_numbers,
    take,
)
from equipment_manager.streaming.pipeline import (
    build_multi_file_pipeline,
    build_pipeline,
)
from equipment_manager.streaming.transformations import (
    cost_differences,
    describe_devices,
    with_running_total,
)


def print_iterator_demo() -> None:
    print("1. Iterator protocol")
    print("-" * 60)

    values: Iterable[int] = [10, 20, 30]
    iterator = iter(values)
    print("next():", next(iterator), next(iterator), next(iterator))

    try:
        next(iterator)
    except StopIteration:
        print("next() after the end -> StopIteration")

    print("iter(list) is list:", iter(values) is values)
    print("iter(iterator) is iterator:", iter(iterator) is iterator)

    numbers = InventoryNumberRange("PC", 1, 4)
    print("Custom iterable, pass 1:", list(numbers))
    print("Custom iterable, pass 2:", list(numbers))
    print("Infinite generator + islice:", take(inventory_numbers(), 3))
    print("yield from (flatten):", list(flatten([1, [2, 3], [4, [5, 6]]])))

    squares_list = [x * x for x in range(1_000_000)]
    squares_gen = (x * x for x in range(1_000_000))
    print(
        "Container size: list =",
        f"{sys.getsizeof(squares_list):,} bytes,",
        "generator =",
        f"{sys.getsizeof(squares_gen)} bytes",
    )


def print_devices(title: str, devices: list[Device]) -> None:
    print(f"\n{title}")

    for line in describe_devices(devices):
        print(" ", line)


def run_stream_demo(path: Path, log_stages: bool = False) -> None:
    print_iterator_demo()

    print(f"\n2. Streaming pipeline, source: {path}")
    print("-" * 60)

    pipeline = build_pipeline(path)
    with closing(pipeline):
        print_devices("First 3 valid devices (islice):", take(pipeline, 3))

    stats = ValidationStats()
    statistics = analytics.calculate_statistics(
        build_pipeline(path, stats=stats, log_stages=log_stages)
    )
    print(
        f"\nRecords: valid = {stats.valid}, invalid = {stats.invalid}, "
        f"total = {stats.total}"
    )
    print(f"Total cost:   {statistics.total_cost:.2f}")
    print(f"Average cost: {statistics.average_cost:.2f}")
    print(f"Min / max:    {statistics.minimum_cost} / {statistics.maximum_cost}")

    if statistics.most_expensive is not None:
        expensive = statistics.most_expensive
        print(f"Most expensive: {expensive.full_name} ({expensive.cost:.2f})")

    print("By type:", statistics.by_type)
    print("By manufacturer:", statistics.by_manufacturer)

    print_devices(
        "Manufacturer = Lenovo:",
        list(build_pipeline(path, manufacturer="Lenovo")),
    )
    print_devices(
        "Type = Laptop:",
        list(build_pipeline(path, device_type="laptop")),
    )

    found = find_by_inventory_number(build_pipeline(path), "pc-008")
    print("\nSearch PC-008:", found.full_name if found else "not found")

    print("\nBatches of 4 (number, size, total cost):")
    for number, size, total in batches.summarize_batches(
        batches.batched(build_pipeline(path), 4)
    ):
        print(f"  batch {number}: {size} device(s), {total:.2f}")

    print("\nDynamic batches (total cost <= 60000):")
    for number, size, total in batches.summarize_batches(
        batches.dynamic_batches(build_pipeline(path), 60000)
    ):
        print(f"  batch {number}: {size} device(s), {total:.2f}")

    print("\nRunning total (accumulate), first 5:")
    for device, total in islice(with_running_total(build_pipeline(path)), 5):
        print(f"  {device.inventory_number}: {total:.2f}")

    print("\nCost differences (pairwise), first 5:")
    for difference in islice(cost_differences(build_pipeline(path)), 5):
        print(f"  {difference:+.2f}")

    two_files = build_multi_file_pipeline([path, path])
    print("\nRecords from two files (chain):", sum(1 for _ in two_files))

    print(
        "Count by type with groupby (after sorting):",
        analytics.count_by_type_groupby(build_pipeline(path)),
    )
