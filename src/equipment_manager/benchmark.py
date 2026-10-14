"""Benchmark: search by inventory number in list and in dict."""

from time import perf_counter

from equipment_manager.data import generate_devices
from equipment_manager.processors import (
    create_device_index,
    find_by_inventory_number,
    find_linear,
)

SIZES: tuple[int, ...] = (1_000, 10_000, 100_000)
REPEATS = 100


def run_benchmark(
    sizes: tuple[int, ...] = SIZES,
    repeats: int = REPEATS,
) -> list[tuple[int, float, float, float]]:
    """Return rows (size, list search, dict search, index build) in seconds.

    The searched device is the last one: the worst case for the list.
    """
    rows: list[tuple[int, float, float, float]] = []

    for size in sizes:
        devices = generate_devices(size)
        target = devices[-1].inventory_number

        start = perf_counter()
        index = create_device_index(devices)
        build_time = perf_counter() - start

        start = perf_counter()
        for _ in range(repeats):
            find_linear(devices, target)
        list_time = (perf_counter() - start) / repeats

        start = perf_counter()
        for _ in range(repeats):
            find_by_inventory_number(index, target)
        dict_time = (perf_counter() - start) / repeats

        rows.append((size, list_time, dict_time, build_time))

    return rows


def print_benchmark(rows: list[tuple[int, float, float, float]]) -> None:
    print(
        f"{'Records':>9}{'list search, s':>17}"
        f"{'dict search, s':>17}{'index build, s':>17}"
    )

    for size, list_time, dict_time, build_time in rows:
        print(
            f"{size:>9,}{list_time:>17.9f}"
            f"{dict_time:>17.9f}{build_time:>17.9f}"
        )
