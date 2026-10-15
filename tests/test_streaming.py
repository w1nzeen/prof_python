from collections.abc import Iterator
from itertools import count, islice
from pathlib import Path

import pytest

from equipment_manager.models import Device
from equipment_manager.streaming import analytics, batches
from equipment_manager.streaming.experiment import (
    generate_csv,
    run_early_termination,
    run_experiment,
)
from equipment_manager.streaming.filters import (
    ValidationStats,
    filter_by_manufacturer,
    filter_by_type,
    find_by_inventory_number,
    find_first,
)
from equipment_manager.streaming.iterators import (
    InventoryNumberRange,
    flatten,
    inventory_numbers,
    take,
)
from equipment_manager.streaming.parsers import clean_lines, parse_csv_rows
from equipment_manager.streaming.pipeline import (
    build_multi_file_pipeline,
    build_pipeline,
)
from equipment_manager.streaming.transformations import (
    cost_differences,
    with_running_total,
)

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "input.csv"


@pytest.fixture
def devices() -> list[Device]:
    return list(build_pipeline(SAMPLE))


def test_iterable_creates_independent_iterators() -> None:
    numbers = InventoryNumberRange("PC", 1, 4)
    assert list(numbers) == ["PC-000001", "PC-000002", "PC-000003"]
    assert list(numbers) == ["PC-000001", "PC-000002", "PC-000003"]

    iterator = iter(numbers)
    assert iter(iterator) is iterator
    assert list(iterator) == ["PC-000001", "PC-000002", "PC-000003"]
    assert list(iterator) == []


def test_infinite_generator_with_islice() -> None:
    assert take(inventory_numbers("X", 5), 2) == ["X-000005", "X-000006"]


def test_flatten_yield_from() -> None:
    assert list(flatten([1, [2, 3], [4, [5, 6]]])) == [1, 2, 3, 4, 5, 6]


def test_exhausted_generator_is_empty() -> None:
    values = (x for x in range(3))
    assert list(values) == [0, 1, 2]
    assert list(values) == []


def test_clean_and_parse() -> None:
    lines = ["a,b\n", "\n", "  \n", "1,2\n"]
    assert list(parse_csv_rows(clean_lines(lines))) == [{"a": "1", "b": "2"}]


def test_pipeline_validation_and_normalization(devices: list[Device]) -> None:
    stats = ValidationStats()
    result = list(build_pipeline(SAMPLE, stats=stats))

    assert len(result) == len(devices) == 11
    assert (stats.valid, stats.invalid, stats.total) == (11, 4, 15)

    numbers = {device.inventory_number for device in result}
    assert "PC-013" in numbers and "PC-006" not in numbers
    assert {d.device_type for d in result} >= {"Printer"}


def test_pipeline_is_lazy(tmp_path: Path) -> None:
    pipeline = build_pipeline(tmp_path / "missing.csv")  # no error yet
    with pytest.raises(FileNotFoundError):
        next(pipeline)


def test_filters_and_search(devices: list[Device]) -> None:
    assert len(list(filter_by_manufacturer(devices, " hp "))) == 3
    assert len(list(filter_by_type(devices, "LAPTOP"))) == 5

    found = find_by_inventory_number(devices, "pc-008")
    assert found is not None and found.model == "ProLiant DL20"
    assert find_by_inventory_number(devices, "nope") is None


def test_find_first_stops_early() -> None:
    consumed = 0

    def stream() -> Iterator[int]:
        nonlocal consumed
        for value in count():
            consumed += 1
            yield value

    assert find_first(stream(), lambda value: value == 3) == 3
    assert consumed == 4


def test_statistics_single_pass(devices: list[Device]) -> None:
    result = analytics.calculate_statistics(iter(devices))

    assert result.count == 11
    assert result.total_cost == pytest.approx(282000.5)
    assert result.average_cost == pytest.approx(282000.5 / 11)
    assert (result.minimum_cost, result.maximum_cost) == (3100.0, 74500.0)
    assert result.most_expensive is not None
    assert result.most_expensive.inventory_number == "PC-008"
    assert result.by_type["Laptop"] == 5
    assert result.by_manufacturer == dict(
        analytics.count_by_manufacturer(devices)
    )


def test_separate_aggregations_and_empty(devices: list[Device]) -> None:
    assert analytics.streaming_total_cost(iter(devices)) == pytest.approx(
        282000.5
    )
    assert analytics.streaming_average_cost(iter(devices)) == pytest.approx(
        282000.5 / 11
    )
    assert analytics.streaming_average_cost(iter([])) == 0.0
    assert analytics.find_most_expensive(iter([])) is None
    assert analytics.calculate_statistics(iter([])).count == 0
    assert analytics.count_by_type_groupby(devices) == dict(
        analytics.count_by_type(devices)
    )


def test_batches(devices: list[Device]) -> None:
    sizes = [len(batch) for batch in batches.batched(devices, 4)]
    assert sizes == [4, 4, 3]

    with pytest.raises(ValueError):
        list(batches.batched(devices, 0))

    for batch in batches.dynamic_batches(devices, 60000):
        assert len(batch) == 1 or sum(d.cost for d in batch) <= 60000

    summary = list(batches.summarize_batches(batches.batched(devices, 5)))
    assert [number for number, _, _ in summary] == [1, 2, 3]


def test_accumulate_and_pairwise(devices: list[Device]) -> None:
    first = list(islice(with_running_total(devices), 3))
    assert [round(total, 2) for _, total in first] == [
        28500.0, 65400.0, 82600.5,
    ]
    differences = list(islice(cost_differences(devices), 2))
    assert differences == pytest.approx([8400.0, -19699.5])


def test_multi_file_pipeline() -> None:
    stats = ValidationStats()
    result = list(build_multi_file_pipeline([SAMPLE, SAMPLE], stats=stats))
    assert len(result) == 22 and stats.invalid == 8


def test_generator_and_experiment(tmp_path: Path) -> None:
    path = tmp_path / "devices.csv"
    generate_csv(path, 1000)
    stats = ValidationStats()
    result = analytics.calculate_statistics(build_pipeline(path, stats=stats))
    assert stats.total == 1000
    assert result.count == stats.valid and stats.invalid > 0

    rows = run_experiment((500, 1000))
    assert [row.records for row in rows] == [500, 1000]
    assert all(row.eager_peak > row.lazy_peak for row in rows)

    early = run_early_termination(5000)
    assert early.lazy_found is not None and early.eager_matches >= 1
