"""Unit tests of Money and InventoryNumber (boundary and invalid values)."""

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from equipment_manager.domain.exceptions import (
    CurrencyMismatchError,
    InvalidValueError,
)
from equipment_manager.domain.value_objects import InventoryNumber, Money


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param("0", "0.00", id="minimum"),
        pytest.param("0.004", "0.00", id="rounds-down-below-half-cent"),
        pytest.param("0.005", "0.01", id="rounds-half-up"),
        pytest.param("0.01", "0.01", id="one-cent"),
        pytest.param(28500, "28500.00", id="integer"),
        pytest.param(17200.5, "17200.50", id="float"),
        pytest.param("9999999999999999999999.99", "9999999999999999999999.99", id="very-large"),
    ],
)
def test_valid_cost_boundaries(raw: object, expected: str) -> None:
    money = Money.of(raw)  # type: ignore[arg-type]

    assert money.amount == Decimal(expected)
    assert str(money) == f"{expected} UAH"


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param("-0.01", id="just-below-zero"),
        pytest.param(-1, id="negative"),
        pytest.param("NaN", id="nan"),
        pytest.param("Infinity", id="infinity"),
        pytest.param("abc", id="not-a-number"),
        pytest.param("", id="empty-string"),
    ],
)
def test_invalid_cost_is_rejected(raw: object) -> None:
    with pytest.raises(InvalidValueError):
        Money.of(raw)  # type: ignore[arg-type]


def test_negative_cost_message_mentions_negative() -> None:
    with pytest.raises(InvalidValueError, match="negative"):
        Money.of(-5)


@pytest.mark.parametrize("code", ["", "UA", "UAHH", "U1H", "12 "])
def test_invalid_currency_codes(code: str) -> None:
    with pytest.raises(InvalidValueError):
        Money.of(1, code)


def test_currency_is_normalized() -> None:
    assert Money.of(1, " usd ").currency == "USD"


def test_addition_and_multiplication_use_exact_decimals() -> None:
    assert Money.of("0.1") + Money.of("0.2") == Money.of("0.3")
    assert Money.of("19.99") * 3 == Money.of("59.97")
    assert 2 * Money.of(5) == Money.of(10)


def test_division_and_average_rounding() -> None:
    assert Money.of(10) / 3 == Money.of("3.33")

    with pytest.raises(InvalidValueError, match="positive"):
        Money.of(10) / 0


def test_money_comparison_and_hashing() -> None:
    assert Money.of(1) < Money.of(2)
    assert Money.of(2) >= Money.of(2)
    assert len({Money.of(5), Money.of("5.00")}) == 1


def test_mixed_currency_operations_raise_custom_exception(currency: str) -> None:
    other = "USD" if currency != "USD" else "EUR"

    with pytest.raises(CurrencyMismatchError, match="mismatch"):
        Money.of(1, currency) + Money.of(1, other)

    with pytest.raises(CurrencyMismatchError):
        _ = Money.of(1, currency) < Money.of(1, other)


def test_money_is_immutable() -> None:
    money = Money.of(5)

    with pytest.raises(AttributeError):
        money.amount = Decimal(1)  # type: ignore[misc]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("PC-001", "PC-001"),
        ("pc-001", "PC-001"),
        ("  Pc-12 ", "PC-12"),
        ("A-1", "A-1"),
        ("ABCDE-123456789", "ABCDE-123456789"),
    ],
)
def test_valid_inventory_numbers(raw: str, expected: str) -> None:
    assert str(InventoryNumber(raw)) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "PC001",
        "PC-",
        "-001",
        "PC--1",
        "ABCDEF-1",
        "PC-1234567890",
        "PC-1A",
        "PC 001",
        "PC-001\nPC-002",
    ],
)
def test_invalid_inventory_numbers(raw: str) -> None:
    with pytest.raises(InvalidValueError, match="inventory number"):
        InventoryNumber(raw)


def test_parse_returns_same_object_for_inventory_number() -> None:
    number = InventoryNumber("PC-001")

    assert InventoryNumber.parse(number) is number
    assert InventoryNumber.parse("pc-001") == number


@given(st.integers(min_value=0, max_value=10**12), st.integers(min_value=0, max_value=10**12))
def test_addition_is_commutative_property(first: int, second: int) -> None:
    assert Money.of(first) + Money.of(second) == Money.of(second) + Money.of(first)


@given(st.integers(min_value=0, max_value=10**9))
def test_total_of_equal_parts_property(cents: int) -> None:
    money = Money.of(Decimal(cents) / 100)

    assert money * 3 == money + money + money


@given(st.from_regex(r"[A-Za-z]{1,5}-[0-9]{1,9}", fullmatch=True))
def test_inventory_number_normalization_is_idempotent(raw: str) -> None:
    once = InventoryNumber(raw)

    assert InventoryNumber(str(once)) == once
    assert str(once) == str(once).upper()
