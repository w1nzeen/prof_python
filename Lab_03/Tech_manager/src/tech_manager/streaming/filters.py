"""Validation та filtering stages."""

import math
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field

from tech_manager.streaming.records import TechRecord


@dataclass
class ValidationReport:
    """Лічильники valid/invalid records (заповнюється під час споживання)."""

    valid: int = 0
    invalid: int = 0
    reasons: Counter[str] = field(default_factory=Counter)

    @property
    def total(self) -> int:
        return self.valid + self.invalid


def _text(row: dict[str, str], name: str) -> str:
    value = row.get(name)
    if value is None:
        raise ValueError(f"missing {name}")
    value = value.strip()
    if not value:
        raise ValueError(f"empty {name}")
    return value


def build_record(row: dict[str, str]) -> TechRecord:
    """Перевіряє один рядок; при помилці піднімає ValueError з причиною."""
    inventory_number = _text(row, "inventory_number")
    tech_type = _text(row, "type")
    manufacturer = _text(row, "manufacturer")
    model = _text(row, "model")
    raw_cost = _text(row, "cost")
    try:
        cost = float(raw_cost)
    except ValueError:
        raise ValueError("cost is not a number") from None
    if not math.isfinite(cost):
        raise ValueError("cost is not finite")
    if cost <= 0:
        raise ValueError("cost must be positive")
    return TechRecord(inventory_number, tech_type, manufacturer, model, cost)


def parse_record(row: dict[str, str]) -> TechRecord | None:
    """Те саме, але повертає None замість винятку (для eager-версії)."""
    try:
        return build_record(row)
    except ValueError:
        return None


def validate_records(
    rows: Iterable[dict[str, str]],
    report: ValidationReport | None = None,
) -> Iterator[TechRecord]:
    """Validation stage: пропускає лише коректні записи, рахує invalid."""
    for row in rows:
        try:
            record = build_record(row)
        except ValueError as error:
            if report is not None:
                report.invalid += 1
                report.reasons[str(error)] += 1
            continue
        if report is not None:
            report.valid += 1
        yield record


def filter_records(
    records: Iterable[TechRecord],
    predicate: Callable[[TechRecord], bool],
) -> Iterator[TechRecord]:
    """Універсальна lazy-фільтрація."""
    for record in records:
        if predicate(record):
            yield record


def filter_by_manufacturer(
    records: Iterable[TechRecord], *manufacturers: str
) -> Iterator[TechRecord]:
    """Фільтр за одним або кількома виробниками (регістр не важливий)."""
    allowed = {name.lower() for name in manufacturers}
    for record in records:
        if record.manufacturer.lower() in allowed:
            yield record


def filter_by_type(
    records: Iterable[TechRecord], *types: str
) -> Iterator[TechRecord]:
    """Фільтр за типом пристрою."""
    allowed = {name.lower() for name in types}
    for record in records:
        if record.type.lower() in allowed:
            yield record


def filter_by_cost(
    records: Iterable[TechRecord],
    minimum: float = 0.0,
    maximum: float = math.inf,
) -> Iterator[TechRecord]:
    """Фільтр за діапазоном вартості."""
    for record in records:
        if minimum <= record.cost <= maximum:
            yield record
