"""Демонстрація потокового конвеєра (Lab 03, варіант 13).

Запуск: python -m tech_manager.streaming.main [шлях_до_csv]
"""

import sys
from collections import Counter
from itertools import dropwhile, islice, takewhile
from pathlib import Path

from tech_manager.analytics import calculate_total_price
from tech_manager.streaming.analytics import (
    calculate_statistics,
    cost_by_manufacturer,
    cost_differences,
    count_by_manufacturer,
    count_by_type,
    cumulative_cost,
    find_most_expensive,
    streaming_average,
    streaming_total,
)
from tech_manager.streaming.batches import batched, batched_by_cost, summarize_batches
from tech_manager.streaming.filters import ValidationReport
from tech_manager.streaming.generators import (
    demo_yield_states,
    even_numbers,
    flatten,
    inventory_numbers,
    natural_numbers,
)
from tech_manager.streaming.iterators import InventoryNumberRange, NumberRange
from tech_manager.streaming.pipeline import (
    build_multi_file_stream,
    build_stream,
    export_csv,
)
from tech_manager.streaming.search import find_by_inventory_number, take
from tech_manager.streaming.transformations import short_descriptions, to_tech_objects

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def locate(name: str) -> Path:
    """Шукає data/<name> у поточній теці, потім у корені проєкту."""
    for base in (Path.cwd(), PROJECT_ROOT):
        candidate = base / "data" / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"data/{name} not found")


def title(text: str) -> None:
    print(f"\n=== {text} ===")


def show_iterator_protocol() -> None:
    title("1. Iterable та iterator")
    values = [10, 20, 30]
    iterator = iter(values)
    print("iter(list) is list:", iter(values) is values)
    print("iter(iterator) is iterator:", iter(iterator) is iterator)
    print("next x3:", next(iterator), next(iterator), next(iterator))
    try:
        next(iterator)
    except StopIteration:
        print("4-й next() -> StopIteration")

    numbers = NumberRange(1, 5)
    print("NumberRange, 1-й обхід:", list(numbers))
    print("NumberRange, 2-й обхід:", list(numbers), "(новий iterator)")
    print("InventoryNumberRange:", list(InventoryNumberRange(1, 4)))

    exhausted = (x for x in range(3))
    print("generator, 1-й обхід:", list(exhausted))
    print("generator, 2-й обхід:", list(exhausted), "(exhausted)")


def show_generators() -> None:
    title("2. Generator functions, yield, yield from")
    demo = demo_yield_states()
    print("generator створено, тіло ще не виконувалось")
    print("next ->", next(demo))
    print("next ->", next(demo))
    print("even_numbers(10):", list(even_numbers(10)))
    print("flatten:", list(flatten([1, [2, 3], [4, [5, 6]]])))
    print("natural_numbers + islice:", list(islice(natural_numbers(), 5)))
    print("inventory_numbers + islice:", list(islice(inventory_numbers(), 3)))
    print("takewhile(<5):", list(takewhile(lambda x: x < 5, [1, 2, 3, 10, 2])))
    print("dropwhile(<5):", list(dropwhile(lambda x: x < 5, [1, 2, 3, 10, 2])))


def show_pipeline(path: Path, path2: Path) -> None:
    title("3. Lazy pipeline: input.csv")
    print("Схема: read_lines -> clean_lines -> parse_csv_rows -> validate_records")
    print("       -> normalize_records -> filters -> aggregation / batching")

    report = ValidationReport()
    counts: Counter[str] = Counter()
    stream = build_stream(path, report=report, counts=counts)
    print("pipeline створено; рядків прочитано:", counts["rows"] or 0)
    stats = calculate_statistics(stream)
    print("після споживання -> stage counters:", dict(counts))
    print(f"valid={report.valid}, invalid={report.invalid}")
    print("причини invalid:", dict(report.reasons))

    print(f"\nCount: {stats.count}")
    print(f"Total cost:   {stats.total:.2f}")
    print(f"Average cost: {stats.average:.2f}")
    print(f"Min / Max:    {stats.minimum} / {stats.maximum}")
    if stats.most_expensive:
        print("Most expensive:", stats.most_expensive.name, stats.most_expensive.cost)
    print("Count by type:", stats.by_type)
    print("Count by manufacturer:", stats.by_manufacturer)

    title("4. Окремі streaming-агрегації (кожна - новий pipeline)")
    print("streaming_average:", round(streaming_average(build_stream(path)), 2))
    print("streaming_total:  ", round(streaming_total(build_stream(path)), 2))
    print("most expensive:   ", find_most_expensive(build_stream(path)).name)
    print("count_by_type:    ", dict(count_by_type(build_stream(path))))
    print("count_by_vendor:  ", dict(count_by_manufacturer(build_stream(path))))
    total_lab2 = calculate_total_price(to_tech_objects(build_stream(path)))
    print("total через Lab 02 (Tech + generator):", round(total_lab2, 2))

    title("5. Фільтрація, пошук, islice")
    dell_hp = build_stream(path, manufacturers=("dell", "HP"))
    print("Dell/HP:", [r.inventory_number for r in dell_hp])
    laptops = build_stream(path, types=("laptop",))
    print("Laptop (нормалізований тип):", [r.inventory_number for r in laptops])
    combo = build_stream(path, manufacturers=("Dell",), types=("Laptop",), min_cost=1000)
    print("Dell + Laptop + cost >= 1000:", [r.inventory_number for r in combo])
    print("Пошук '008':", find_by_inventory_number(build_stream(path), "008"))
    print("Пошук '999':", find_by_inventory_number(build_stream(path), "999"))
    print("Перші 3 (islice):")
    for line in short_descriptions(take(build_stream(path), 3)):
        print("  ", line)

    title("6. Batch processing")
    for index, size, total in summarize_batches(batched(build_stream(path), 4)):
        print(f"  batch {index}: {size} записів, сума {total:.2f}")
    print("Dynamic batching (сума <= 3000):")
    for index, size, total in summarize_batches(batched_by_cost(build_stream(path), 3000)):
        print(f"  batch {index}: {size} записів, сума {total:.2f}")

    title("7. itertools: accumulate, pairwise, groupby, chain")
    first5 = lambda: islice(build_stream(path), 5)  # noqa: E731
    print("accumulate:", list(cumulative_cost(first5())))
    print("pairwise diff:", list(cost_differences(first5())))
    print("groupby (manufacturer, count, total):")
    for manufacturer, count, total in cost_by_manufacturer(build_stream(path)):
        print(f"  {manufacturer:8} {count}  {total:9.2f}")

    report2 = ValidationReport()
    multi = build_multi_file_stream([path, path2], report=report2)
    total_multi = sum(1 for _ in multi)
    print(f"chain (2 файли): {total_multi} valid, {report2.invalid} invalid")

    title("8. Streaming export")
    target = Path("export_expensive.csv")
    written = export_csv(build_stream(path, min_cost=1000), target)
    print(f"У {target} записано {written} записів (cost >= 1000)")


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else locate("input.csv")
    path2 = locate("input_part2.csv")
    show_iterator_protocol()
    show_generators()
    show_pipeline(path, path2)


if __name__ == "__main__":
    main()
