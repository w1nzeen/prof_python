"""Transformation stage."""

from collections.abc import Iterable, Iterator

from tech_manager.models import Tech
from tech_manager.streaming.records import TechRecord


def normalize_record(record: TechRecord) -> TechRecord:
    """Нормалізація одного запису: тип - Capitalize, зайві пробіли, ціна."""
    return record._replace(
        type=record.type.capitalize(),
        manufacturer=" ".join(record.manufacturer.split()),
        model=" ".join(record.model.split()),
        cost=round(record.cost, 2),
    )


def normalize_records(records: Iterable[TechRecord]) -> Iterator[TechRecord]:
    for record in records:
        yield normalize_record(record)


def to_tech_objects(records: Iterable[TechRecord]) -> Iterator[Tech]:
    """Міст до Lab 01/02: TechRecord -> Tech (generator expression)."""
    return (record.to_tech() for record in records)


def short_descriptions(records: Iterable[TechRecord]) -> Iterator[str]:
    """Lazy transformation у короткий текстовий вигляд."""
    for record in records:
        yield f"{record.inventory_number} {record.name} ({record.cost:.2f})"
