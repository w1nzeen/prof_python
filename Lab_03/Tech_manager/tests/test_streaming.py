"""Тести Lab 03: iterators, generators, pipeline, batching, eager vs lazy."""

from collections import Counter
from itertools import islice
from pathlib import Path

import pytest

from tech_manager.streaming.analytics import (
    calculate_statistics,
    cost_by_manufacturer,
    cost_differences,
    count_by_type,
    cumulative_cost,
    find_most_expensive,
    streaming_average,
    streaming_total,
)
from tech_manager.streaming.batches import batched, batched_by_cost, summarize_batches
from tech_manager.streaming.datagen import generate_test_file
from tech_manager.streaming.eager import eager_find_first, eager_pipeline
from tech_manager.streaming.experiment import lazy_pipeline
from tech_manager.streaming.filters import ValidationReport, parse_record, validate_records
from tech_manager.streaming.generators import (
    even_numbers,
    flatten,
    inventory_numbers,
    natural_numbers,
)
from tech_manager.streaming.iterators import (
    InventoryNumberRange,
    NumberRange,
    NumberRangeIterator,
)
from tech_manager.streaming.pipeline import (
    build_multi_file_stream,
    build_stream,
    export_csv,
)
from tech_manager.streaming.readers import clean_lines, read_lines
from tech_manager.streaming.records import TechRecord
from tech_manager.streaming.search import find_by_inventory_number, find_first, take

CSV_TEXT = """inventory_number,type,manufacturer,model,cost
001,Laptop,Dell,XPS 13,1000.00
002,laptop, HP ,Spectre,1200.50

003,Monitor,Dell,U2723QE,500
004,Tablet,Apple,iPad,abc
005,Tablet,Apple,,300
006,Phone,Google,Pixel,-5
007,Phone,Google
008,Phone,Samsung,S23,inf
009,Monitor,LG,UltraFine,700
"""


@pytest.fixture
def csv_file(tmp_path: Path) -> Path:
    path = tmp_path / "input.csv"
    path.write_text(CSV_TEXT, encoding="utf-8")
    return path


# ---------------- iterators / generators ----------------
def test_iterator_protocol_and_exhaustion():
    iterator = iter([1, 2])
    assert iter(iterator) is iterator
    assert (next(iterator), next(iterator)) == (1, 2)
    with pytest.raises(StopIteration):
        next(iterator)


def test_number_range_is_reusable_and_iterator_is_one_shot():
    numbers = NumberRange(1, 4)
    assert list(numbers) == [1, 2, 3]
    assert list(numbers) == [1, 2, 3]
    iterator = NumberRangeIterator(1, 3)
    assert list(iterator) == [1, 2]
    assert list(iterator) == []


def test_inventory_number_range():
    assert list(InventoryNumberRange(1, 4)) == ["000001", "000002", "000003"]


def test_generator_functions():
    assert list(even_numbers(7)) == [0, 2, 4, 6]
    assert list(flatten([1, [2, [3, 4]], 5])) == [1, 2, 3, 4, 5]
    assert list(islice(natural_numbers(), 3)) == [1, 2, 3]
    assert list(islice(inventory_numbers(9), 2)) == ["000009", "000010"]


def test_exhausted_generator_is_empty():
    values = (x for x in range(3))
    assert list(values) == [0, 1, 2]
    assert list(values) == []


# ---------------- reading / validation ----------------
def test_read_lines_is_lazy(tmp_path: Path):
    lines = read_lines(tmp_path / "missing.csv")  # помилки ще немає
    with pytest.raises(FileNotFoundError):
        next(lines)  # lazy exception - лише при споживанні


def test_clean_lines_drops_blank(csv_file: Path):
    lines = list(clean_lines(read_lines(csv_file)))
    assert all(line.strip() for line in lines)
    assert len(lines) == 10  # header + 9 рядків даних


def test_validation_counts_invalid(csv_file: Path):
    report = ValidationReport()
    records = list(build_stream(csv_file, report=report))
    assert [r.inventory_number for r in records] == ["001", "002", "003", "009"]
    assert (report.valid, report.invalid, report.total) == (4, 5, 9)
    assert report.reasons["cost is not a number"] == 1
    assert report.reasons["empty model"] == 1
    assert report.reasons["cost must be positive"] == 1
    assert report.reasons["missing model"] == 1
    assert report.reasons["cost is not finite"] == 1


def test_parse_record():
    good = {"inventory_number": "1", "type": "A", "manufacturer": "B",
            "model": "C", "cost": " 10.5 "}
    assert parse_record(good) == TechRecord("1", "A", "B", "C", 10.5)
    assert parse_record({**good, "cost": "x"}) is None
    assert list(validate_records([good, {**good, "model": ""}])) == [
        TechRecord("1", "A", "B", "C", 10.5)
    ]


# ---------------- filters / transformation ----------------
def test_filters_and_normalization(csv_file: Path):
    hp = list(build_stream(csv_file, manufacturers=("hp",)))
    assert [r.manufacturer for r in hp] == ["HP"]  # пробіли прибрано
    laptops = list(build_stream(csv_file, types=("LAPTOP",)))
    assert [r.type for r in laptops] == ["Laptop", "Laptop"]  # capitalize
    costly = list(build_stream(csv_file, min_cost=1000, max_cost=1100))
    assert [r.inventory_number for r in costly] == ["001"]


def test_pipeline_is_lazy_and_counts_stages(csv_file: Path):
    counts: Counter[str] = Counter()
    stream = build_stream(csv_file, counts=counts)
    assert counts == Counter()  # нічого не прочитано до споживання
    next(stream)
    assert counts["rows"] < 9
    stream.close()


# ---------------- search / early termination ----------------
def test_find_first_stops_early():
    consumed = []

    def source():
        for number in range(1000):
            consumed.append(number)
            yield TechRecord(str(number), "T", "V", "M", float(number))

    found = find_first(source(), lambda r: r.cost >= 5)
    assert found.inventory_number == "5"
    assert consumed == [0, 1, 2, 3, 4, 5]


def test_find_by_inventory_number_and_take(csv_file: Path):
    assert find_by_inventory_number(build_stream(csv_file), "003").model == "U2723QE"
    assert find_by_inventory_number(build_stream(csv_file), "999") is None
    assert len(take(build_stream(csv_file), 2)) == 2


# ---------------- batching ----------------
def test_batched_sizes_and_validation():
    items = [TechRecord(str(i), "T", "V", "M", 1.0) for i in range(7)]
    assert [len(b) for b in batched(items, 3)] == [3, 3, 1]
    assert list(batched([], 3)) == []
    with pytest.raises(ValueError):
        batched(items, 0)


def test_dynamic_batching():
    costs = [400, 400, 400, 900, 100]
    items = [TechRecord(str(i), "T", "V", "M", float(c)) for i, c in enumerate(costs)]
    batches = list(batched_by_cost(items, 1000))
    assert [[r.cost for r in b] for b in batches] == [[400, 400], [400], [900, 100]]
    summary = list(summarize_batches(batches))
    assert summary[0] == (1, 2, 800.0)


# ---------------- analytics ----------------
def test_streaming_analytics(csv_file: Path):
    def stream():
        return build_stream(csv_file)

    assert streaming_total(stream()) == pytest.approx(3400.5)
    assert streaming_average(stream()) == pytest.approx(3400.5 / 4)
    assert find_most_expensive(stream()).inventory_number == "002"
    assert find_most_expensive([]) is None
    assert streaming_average([]) == 0.0
    assert dict(count_by_type(stream())) == {"Laptop": 2, "Monitor": 2}
    stats = calculate_statistics(stream())
    assert (stats.count, stats.minimum, stats.maximum) == (4, 500.0, 1200.5)
    assert stats.most_expensive.inventory_number == "002"


def test_itertools_analytics(csv_file: Path):
    assert list(cumulative_cost(build_stream(csv_file))) == [
        1000.0, 2200.5, 2700.5, 3400.5,
    ]
    assert list(cost_differences(build_stream(csv_file))) == [200.5, -700.5, 200.0]
    groups = {m: (n, t) for m, n, t in cost_by_manufacturer(build_stream(csv_file))}
    assert groups["Dell"] == (2, 1500.0)


def test_multi_file_and_export(csv_file: Path, tmp_path: Path):
    second = tmp_path / "second.csv"
    second.write_text(
        "inventory_number,type,manufacturer,model,cost\n101,Laptop,Acer,Swift,800\n",
        encoding="utf-8",
    )
    stream = build_multi_file_stream([csv_file, second])
    assert len(list(stream)) == 5  # 4 + 1, заголовки не потрапили в дані
    target = tmp_path / "out.csv"
    assert export_csv(build_stream(csv_file, min_cost=1000), target) == 2
    assert len(list(build_stream(target))) == 2  # експорт можна прочитати назад


# ---------------- eager vs lazy ----------------
def test_datagen_is_deterministic_and_large_enough(tmp_path: Path):
    a = generate_test_file(tmp_path / "a.csv", 2000)
    b = generate_test_file(tmp_path / "b.csv", 2000)
    assert a.read_text(encoding="utf-8") == b.read_text(encoding="utf-8")
    report = ValidationReport()
    valid = sum(1 for _ in build_stream(a, report=report))
    assert report.total == 2000 and 0 < report.invalid < 100
    assert valid == report.valid


def test_eager_and_lazy_give_same_result(tmp_path: Path):
    path = generate_test_file(tmp_path / "data.csv", 5000)
    assert eager_pipeline(path, 1500.0) == lazy_pipeline(path, 1500.0)
    found_lazy = find_first(build_stream(path), lambda r: r.cost >= 2900)
    assert found_lazy == eager_find_first(path, lambda r: r.cost >= 2900)


def test_tech_record_bridge_to_lab2():
    record = TechRecord("001", "Laptop", "Dell", "XPS 13", 999.99)
    tech = record.to_tech()
    assert tech.vendor == "Dell" and tech.price == 999.99
    assert tech.name == record.name
