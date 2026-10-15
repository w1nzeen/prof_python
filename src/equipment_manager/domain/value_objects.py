"""Immutable value objects: Money and InventoryNumber."""

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from functools import total_ordering
from typing import TypeAlias

from equipment_manager.domain.exceptions import (
    CurrencyMismatchError,
    InvalidValueError,
)

CENT = Decimal("0.01")
INVENTORY_PATTERN = re.compile(r"^[A-Z]{1,5}-\d{1,9}$")


@total_ordering
@dataclass(frozen=True, slots=True)
class Money:
    """Non-negative amount of money with two decimal places."""

    amount: Decimal
    currency: str = "UAH"

    def __post_init__(self) -> None:
        if not self.amount.is_finite():
            raise InvalidValueError("Money amount must be finite")

        if self.amount < 0:
            raise InvalidValueError("Money amount cannot be negative")

        currency = self.currency.strip().upper()

        if len(currency) != 3 or not currency.isalpha():
            raise InvalidValueError(f"Invalid currency: {self.currency!r}")

        # frozen dataclass: normalization needs object.__setattr__
        rounded = self.amount.quantize(CENT, rounding=ROUND_HALF_UP)
        object.__setattr__(self, "amount", rounded)
        object.__setattr__(self, "currency", currency)

    @classmethod
    def of(
        cls,
        amount: float | str | Decimal,
        currency: str = "UAH",
    ) -> "Money":
        """Convenient factory: Money.of(35000.5)."""
        try:
            value = (
                amount if isinstance(amount, Decimal) else Decimal(str(amount))
            )
        except InvalidOperation as error:
            raise InvalidValueError(
                f"Invalid money amount: {amount!r}"
            ) from error

        return cls(value, currency)

    @classmethod
    def zero(cls, currency: str = "UAH") -> "Money":
        return cls(Decimal(0), currency)

    def _check_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError(
                f"Currency mismatch: {self.currency} and {other.currency}"
            )

    def __add__(self, other: "Money") -> "Money":
        self._check_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __mul__(self, factor: int | Decimal) -> "Money":
        return Money(self.amount * factor, self.currency)

    def __rmul__(self, factor: int | Decimal) -> "Money":
        return self.__mul__(factor)

    def __truediv__(self, divisor: int) -> "Money":
        if divisor <= 0:
            raise InvalidValueError("Divisor must be positive")

        return Money(self.amount / divisor, self.currency)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented

        self._check_currency(other)
        return self.amount < other.amount

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}"

    def to_dict(self) -> dict[str, object]:
        return {"amount": str(self.amount), "currency": self.currency}


@dataclass(frozen=True, slots=True)
class InventoryNumber:
    """Validated inventory number such as PC-001."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()

        if not INVENTORY_PATTERN.match(normalized):
            raise InvalidValueError(
                f"Invalid inventory number: {self.value!r}"
            )

        object.__setattr__(self, "value", normalized)

    @classmethod
    def parse(cls, value: "str | InventoryNumber") -> "InventoryNumber":
        if isinstance(value, InventoryNumber):
            return value

        return cls(value)

    def __str__(self) -> str:
        return self.value


NumberLike: TypeAlias = InventoryNumber | str
