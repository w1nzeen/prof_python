"""Запис інвентарного файлу: NamedTuple, який передається між stages pipeline."""

from typing import NamedTuple

from tech_manager.models import Tech

# Порядок колонок input.csv (варіант 13).
CSV_FIELDS: tuple[str, ...] = (
    "inventory_number",
    "type",
    "manufacturer",
    "model",
    "cost",
)


class TechRecord(NamedTuple):
    """Один валідний рядок input.csv. Незмінний і легкий (tuple)."""

    inventory_number: str
    type: str
    manufacturer: str
    model: str
    cost: float

    @property
    def name(self) -> str:
        return f"{self.type}: {self.manufacturer} {self.model}"

    def to_tech(self) -> Tech:
        """Перетворення на dataclass Tech з Lab 01 / Lab 02."""
        return Tech(
            inventory_number=self.inventory_number,
            type=self.type,
            vendor=self.manufacturer,
            model=self.model,
            price=self.cost,
        )
