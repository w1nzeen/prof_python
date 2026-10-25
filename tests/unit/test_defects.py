"""Regression tests for defects that were found by boundary testing.

Every test here failed on the code as it was after laboratory work 5
and passes after the fix (see the report, section "Found defects").
"""

import pytest

from equipment_manager.domain.exceptions import InvalidValueError
from equipment_manager.domain.value_objects import InventoryNumber, Money
from equipment_manager.importer.exceptions import RecordValidationError
from equipment_manager.importer.models import RawRecord
from equipment_manager.importer.validators import ValidationRules, validate_record

RULES = ValidationRules.from_lists(["Laptop"], ["Dell"])


def raw(**changes: object) -> RawRecord:
    data: dict[str, object] = {
        "inventory_number": "PC-001",
        "type": "Laptop",
        "manufacturer": "Dell",
        "model": "XPS",
        "value": "100",
    }
    data.update(changes)

    return RawRecord(2, data)


# Defect 1: decimal.InvalidOperation leaked out of Money
@pytest.mark.parametrize("amount", ["1e30", "1E+26", 10**40, 1e30])
def test_huge_amount_is_a_domain_error(amount: object) -> None:
    with pytest.raises(InvalidValueError, match="too large"):
        Money.of(amount)  # type: ignore[arg-type]


# Defect 2: non-ASCII digits were accepted in inventory numbers
@pytest.mark.parametrize("number", ["PC-００１", "PC-٣", "PC-१२३"])
def test_non_ascii_digits_are_not_valid_inventory_numbers(number: str) -> None:
    with pytest.raises(InvalidValueError):
        InventoryNumber(number)


def test_importer_rejects_non_ascii_inventory_digits() -> None:
    with pytest.raises(RecordValidationError) as exc_info:
        validate_record(raw(inventory_number="PC-００１"), RULES)

    assert exc_info.value.field == "inventory_number"


# Defect 3: float() accepts underscores and non-ASCII digits
@pytest.mark.parametrize("value", ["1_000", "١٢٣", "１２３", "1__0"])
def test_importer_accepts_only_plain_ascii_numbers(value: str) -> None:
    with pytest.raises(RecordValidationError) as exc_info:
        validate_record(raw(value=value), RULES)

    assert exc_info.value.field == "value"
