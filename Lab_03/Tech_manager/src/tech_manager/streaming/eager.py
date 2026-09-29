"""Eager-версія pipeline: кожний stage створює повний list (для порівняння)."""

import csv
from collections.abc import Callable
from pathlib import Path

from tech_manager.streaming.analytics import StreamStatistics, calculate_statistics
from tech_manager.streaming.filters import parse_record
from tech_manager.streaming.records import TechRecord
from tech_manager.streaming.transformations import normalize_record


def read_all_rows(path: Path) -> list[dict[str, str]]:
    """Уся таблиця матеріалізується в пам'яті."""
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def eager_filtered(path: Path, min_cost: float | None = None) -> list[TechRecord]:
    rows = read_all_rows(path)  # list 1
    records = [r for row in rows if (r := parse_record(row)) is not None]  # list 2
    normalized = [normalize_record(r) for r in records]  # list 3
    return [  # list 4
        r for r in normalized if min_cost is None or r.cost >= min_cost
    ]


def eager_pipeline(path: Path, min_cost: float | None = None) -> StreamStatistics:
    return calculate_statistics(eager_filtered(path, min_cost))


def eager_find_first(
    path: Path, predicate: Callable[[TechRecord], bool]
) -> TechRecord | None:
    """Спочатку будує ВЕСЬ list збігів, і лише потім бере перший."""
    matches = [r for r in eager_filtered(path) if predicate(r)]
    return matches[0] if matches else None
