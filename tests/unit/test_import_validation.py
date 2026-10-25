"""Boundary and invalid-data tests of the importer validator."""

import pytest

from equipment_manager.importer.exceptions import RecordValidationError
from equipment_manager.importer.models import EquipmentRecord, RawRecord
from equipment_manager.importer.validators import ValidationRules, validate_record

RULES = ValidationRules.from_lists(
    ["Laptop", "Printer"], ["Lenovo", "HP"], ["in_use", "in_repair"]
)


def make_raw(**changes: object) -> RawRecord:
    data: dict[str, object] = {
        "inventory_number": "PC-001",
        "type": "Laptop",
        "manufacturer": "Lenovo",
        "model": "ThinkPad",
        "value": "100",
    }
    data.update(changes)

    return RawRecord(line_number=5, data=data)


def test_valid_record_is_converted() -> None:
    record = validate_record(make_raw(), RULES)

    assert record == EquipmentRecord("PC-001", "Laptop", "Lenovo", "ThinkPad", 100.0)
    assert record.status == "in_use"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("0", 0.0, id="minimum"),
        pytest.param("0.01", 0.01, id="just-above-minimum"),
        pytest.param("99999.99", 99999.99, id="large"),
        pytest.param("12,5", 12.5, id="decimal-comma"),
        pytest.param(" 7 ", 7.0, id="spaces"),
        pytest.param(3, 3.0, id="json-integer"),
        pytest.param(2.5, 2.5, id="json-float"),
    ],
)
def test_valid_value_boundaries(value: object, expected: float) -> None:
    assert validate_record(make_raw(value=value), RULES).value == pytest.approx(expected)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("-0.01", id="just-below-minimum"),
        pytest.param("-1", id="negative"),
        pytest.param("abc", id="text"),
        pytest.param("1.2.3", id="two-dots"),
        pytest.param("nan", id="nan"),
        pytest.param("inf", id="infinity"),
        pytest.param("", id="empty"),
        pytest.param(None, id="none"),
        pytest.param(True, id="boolean"),
    ],
)
def test_invalid_value_is_reported_for_the_value_field(value: object) -> None:
    with pytest.raises(RecordValidationError) as exc_info:
        validate_record(make_raw(value=value), RULES)

    assert exc_info.value.field == "value"
    assert exc_info.value.line_number == 5


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("in_use", "in_use"),
        ("IN_REPAIR", "in_repair"),
        (" In_Use ", "in_use"),
        ("", "in_use"),
        (None, "in_use"),
    ],
)
def test_status_is_optional_and_normalized(status: object, expected: str) -> None:
    assert validate_record(make_raw(status=status), RULES).status == expected


@pytest.mark.parametrize("status", ["lost", "decommissioned", "in use", "0"])
def test_status_outside_the_allowed_list_is_rejected(status: str) -> None:
    with pytest.raises(RecordValidationError, match="Unknown status") as exc_info:
        validate_record(make_raw(status=status), RULES)

    assert exc_info.value.field == "status"
    assert exc_info.value.value == status


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("type", "Tablet"),
        ("manufacturer", "Apple"),
        ("inventory_number", "PC001"),
        ("inventory_number", ""),
        ("model", ""),
        ("model", "x" * 101),
    ],
)
def test_invalid_text_fields(field: str, value: str) -> None:
    with pytest.raises(RecordValidationError) as exc_info:
        validate_record(make_raw(**{field: value}), RULES)

    assert exc_info.value.field == field


def test_model_length_boundary() -> None:
    assert validate_record(make_raw(model="x" * 100), RULES).model == "x" * 100


def test_rules_are_case_insensitive_and_return_canonical_spelling() -> None:
    record = validate_record(make_raw(type="LAPTOP", manufacturer="hp"), RULES)

    assert (record.type, record.manufacturer) == ("Laptop", "HP")


def test_missing_field_is_reported() -> None:
    data = make_raw().data
    incomplete = RawRecord(7, {k: v for k, v in data.items() if k != "model"})

    with pytest.raises(RecordValidationError, match="missing") as exc_info:
        validate_record(incomplete, RULES)

    assert exc_info.value.field == "model"
    assert exc_info.value.line_number == 7


def test_exception_keeps_original_error_as_cause() -> None:
    with pytest.raises(RecordValidationError) as exc_info:
        validate_record(make_raw(value="wrong"), RULES)

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_validation_is_repeatable() -> None:
    raw = make_raw()

    assert validate_record(raw, RULES) == validate_record(raw, RULES)
