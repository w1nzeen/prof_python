"""Data models: raw record from a file and validated equipment record."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass

FIELDS: tuple[str, ...] = (
    "inventory_number",
    "type",
    "manufacturer",
    "model",
    "value",
)

# key used by readers when a CSV row has more cells than the header
EXTRA_FIELDS_KEY = "__extra_fields__"


@dataclass(frozen=True, slots=True)
class RawRecord:
    """Unvalidated data together with its place in the source."""

    line_number: int
    data: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class EquipmentRecord:
    """Validated record of computer equipment (variant 13)."""

    inventory_number: str
    type: str
    manufacturer: str
    model: str
    value: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
