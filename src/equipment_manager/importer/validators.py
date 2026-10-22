"""Validation of raw records (system boundary)."""

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass

from equipment_manager.importer.exceptions import RecordValidationError
from equipment_manager.importer.models import (
    EXTRA_FIELDS_KEY,
    FIELDS,
    EquipmentRecord,
    RawRecord,
)

INVENTORY_PATTERN = re.compile(r"^[A-Z]{1,5}-\d{1,9}$")
MAX_MODEL_LENGTH = 100


@dataclass(frozen=True)
class ValidationRules:
    """Validation policy object built from the configuration."""

    types: dict[str, str]
    manufacturers: dict[str, str]

    @classmethod
    def from_lists(
        cls,
        types: Iterable[str],
        manufacturers: Iterable[str],
    ) -> "ValidationRules":
        """Map the case-folded name to the canonical spelling."""
        return cls(
            types={item.casefold(): item for item in types},
            manufacturers={item.casefold(): item for item in manufacturers},
        )


def _text(raw: RawRecord, field: str) -> str:
    value = raw.data.get(field)

    if value is None:
        raise RecordValidationError(
            f"Field '{field}' is missing",
            line_number=raw.line_number,
            field=field,
        )

    text = str(value).strip()

    if not text:
        raise RecordValidationError(
            f"Field '{field}' is empty",
            line_number=raw.line_number,
            field=field,
        )

    return text


def _choice(
    raw: RawRecord,
    field: str,
    allowed: dict[str, str],
) -> str:
    text = _text(raw, field)

    try:
        return allowed[text.casefold()]
    except KeyError as error:
        raise RecordValidationError(
            f"Unknown {field}: {text!r}",
            line_number=raw.line_number,
            field=field,
            value=text,
        ) from error


def _value(raw: RawRecord) -> float:
    original = raw.data.get("value")
    text = _text(raw, "value")

    if isinstance(original, bool):
        raise RecordValidationError(
            "Value must be numeric",
            line_number=raw.line_number,
            field="value",
            value=text,
        )

    try:
        number = float(text.replace(",", "."))
    except ValueError as error:
        raise RecordValidationError(
            "Value must be numeric",
            line_number=raw.line_number,
            field="value",
            value=text,
        ) from error

    if not math.isfinite(number) or number < 0:
        raise RecordValidationError(
            "Value must be a non-negative number",
            line_number=raw.line_number,
            field="value",
            value=text,
        )

    return number


def validate_record(raw: RawRecord, rules: ValidationRules) -> EquipmentRecord:
    """Return a valid record or raise RecordValidationError."""
    if EXTRA_FIELDS_KEY in raw.data:
        raise RecordValidationError(
            "Record has more fields than the header",
            line_number=raw.line_number,
        )

    for name in FIELDS:
        if name not in raw.data:
            raise RecordValidationError(
                f"Field '{name}' is missing",
                line_number=raw.line_number,
                field=name,
            )

    number = _text(raw, "inventory_number").upper()

    if not INVENTORY_PATTERN.match(number):
        raise RecordValidationError(
            "Invalid inventory number",
            line_number=raw.line_number,
            field="inventory_number",
            value=number,
        )

    device_type = _choice(raw, "type", rules.types)
    manufacturer = _choice(raw, "manufacturer", rules.manufacturers)
    model = _text(raw, "model")

    if len(model) > MAX_MODEL_LENGTH:
        raise RecordValidationError(
            f"Model is longer than {MAX_MODEL_LENGTH} characters",
            line_number=raw.line_number,
            field="model",
        )

    return EquipmentRecord(
        inventory_number=number,
        type=device_type,
        manufacturer=manufacturer,
        model=model,
        value=_value(raw),
    )
