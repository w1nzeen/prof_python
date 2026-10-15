"""Stages 3 and 4: validation and filtering."""

import math
from collections.abc import Callable, Generator, Iterable
from dataclasses import dataclass
from typing import TypeVar

from equipment_manager.exceptions import InvalidDeviceError
from equipment_manager.models import Device

T = TypeVar("T")


@dataclass
class ValidationStats:
    """Counters filled while the stream is being consumed."""

    valid: int = 0
    invalid: int = 0

    @property
    def total(self) -> int:
        return self.valid + self.invalid


def validate_devices(
    rows: Iterable[dict[str, str]],
    stats: ValidationStats | None = None,
) -> Generator[Device, None, None]:
    """Convert rows to Device objects and skip invalid records."""
    counters = stats if stats is not None else ValidationStats()

    for row in rows:
        try:
            cost = float(row["cost"])

            if not math.isfinite(cost):
                raise ValueError("cost must be a finite number")

            device = Device(
                inventory_number=row["inventory_number"].strip(),
                device_type=row["type"].strip(),
                manufacturer=row["manufacturer"].strip(),
                model=row["model"].strip(),
                cost=cost,
            )
        except (
            KeyError,
            ValueError,
            TypeError,
            AttributeError,
            InvalidDeviceError,
        ):
            counters.invalid += 1
            continue

        counters.valid += 1
        yield device


def filter_items(
    items: Iterable[T],
    predicate: Callable[[T], bool],
) -> Generator[T, None, None]:
    """Universal lazy filter."""
    for item in items:
        if predicate(item):
            yield item


def filter_by_manufacturer(
    devices: Iterable[Device],
    manufacturer: str,
) -> Generator[Device, None, None]:
    name = manufacturer.strip().lower()

    return filter_items(
        devices,
        lambda device: device.manufacturer.lower() == name,
    )


def filter_by_type(
    devices: Iterable[Device],
    device_type: str,
) -> Generator[Device, None, None]:
    name = device_type.strip().lower()

    return filter_items(
        devices,
        lambda device: device.device_type.lower() == name,
    )


def find_first(
    items: Iterable[T],
    predicate: Callable[[T], bool],
) -> T | None:
    """Lazy search with early termination: stops at the first match."""
    for item in items:
        if predicate(item):
            return item

    return None


def find_by_inventory_number(
    devices: Iterable[Device],
    inventory_number: str,
) -> Device | None:
    """Search by inventory number without loading the whole dataset."""
    wanted = inventory_number.strip().lower()

    return find_first(
        devices,
        lambda device: device.inventory_number.lower() == wanted,
    )
