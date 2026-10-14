"""Aggregation, sorting and statistics for devices."""

from collections.abc import Callable
from typing import Any

from equipment_manager.decorators import (
    OPERATION_HISTORY,
    measure_time,
    record_operation,
)
from equipment_manager.models import Device
from equipment_manager.processors import Predicate


def calculate_total_cost(devices: list[Device]) -> float:
    """Generator expression: no intermediate list is created. O(n)."""
    return sum(device.cost for device in devices)


@measure_time
def calculate_average_cost(devices: list[Device]) -> float:
    if not devices:
        return 0.0

    return calculate_total_cost(devices) / len(devices)


@record_operation(OPERATION_HISTORY)
def find_most_expensive(devices: list[Device]) -> Device | None:
    if not devices:
        return None

    return max(devices, key=lambda device: device.cost)


def calculate_cost_range(devices: list[Device]) -> tuple[float, float]:
    """Return (minimum, maximum) cost as a tuple."""
    if not devices:
        return (0.0, 0.0)

    costs = [device.cost for device in devices]

    return (min(costs), max(costs))


def calculate_cost_by_manufacturer(
    devices: list[Device],
) -> dict[str, float]:
    """Aggregation: total cost of equipment of each manufacturer."""
    totals: dict[str, float] = {}

    for device in devices:
        totals[device.manufacturer] = (
            totals.get(device.manufacturer, 0.0) + device.cost
        )

    return totals


def sort_devices(
    devices: list[Device],
    key: Callable[[Device], Any],
    reverse: bool = False,
) -> list[Device]:
    """Universal sorting, O(n log n)."""
    return sorted(devices, key=key, reverse=reverse)


def sort_by_cost(devices: list[Device], reverse: bool = True) -> list[Device]:
    return sort_devices(
        devices,
        key=lambda device: device.cost,
        reverse=reverse,
    )


def calculate_average_values(*values: float) -> float:
    """*args: average of any number of values."""
    if not values:
        return 0.0

    return sum(values) / len(values)


def create_device(**fields: Any) -> Device:
    """**kwargs: build a Device from keyword arguments."""
    return Device(**fields)


def create_cost_filter(
    minimum: float,
    maximum: float | None = None,
) -> Predicate:
    """Closure: `predicate` remembers `minimum` and `maximum`."""

    def predicate(device: Device) -> bool:
        if device.cost < minimum:
            return False

        return maximum is None or device.cost <= maximum

    return predicate


def create_manufacturer_filter(manufacturer: str) -> Predicate:
    """Closure that remembers the manufacturer name."""
    name = manufacturer.strip().lower()

    def predicate(device: Device) -> bool:
        return device.manufacturer.lower() == name

    return predicate
