"""Stage 6: aggregation of a stream in a single pass."""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from itertools import groupby

from equipment_manager.models import Device


@dataclass(frozen=True)
class StreamStatistics:
    count: int
    total_cost: float
    average_cost: float
    minimum_cost: float | None
    maximum_cost: float | None
    most_expensive: Device | None
    by_type: dict[str, int] = field(default_factory=dict)
    by_manufacturer: dict[str, int] = field(default_factory=dict)


def streaming_total_cost(devices: Iterable[Device]) -> float:
    """Generator expression: no intermediate list."""
    return sum(device.cost for device in devices)


def streaming_average_cost(devices: Iterable[Device]) -> float:
    total = 0.0
    count = 0

    for device in devices:
        total += device.cost
        count += 1

    return total / count if count else 0.0


def find_most_expensive(devices: Iterable[Device]) -> Device | None:
    return max(devices, key=lambda device: device.cost, default=None)


def count_by_type(devices: Iterable[Device]) -> Counter[str]:
    return Counter(device.device_type for device in devices)


def count_by_manufacturer(devices: Iterable[Device]) -> Counter[str]:
    return Counter(device.manufacturer for device in devices)


def count_by_type_groupby(devices: Iterable[Device]) -> dict[str, int]:
    """groupby groups only NEIGHBOURING items, so sorting is required.

    Sorting materializes the stream, so use this only for small data.
    """
    ordered = sorted(devices, key=lambda device: device.device_type)

    return {
        device_type: sum(1 for _ in group)
        for device_type, group in groupby(
            ordered,
            key=lambda device: device.device_type,
        )
    }


def calculate_statistics(devices: Iterable[Device]) -> StreamStatistics:
    """All statistics in one pass; memory does not depend on stream size."""
    count = 0
    total = 0.0
    minimum: float | None = None
    maximum: float | None = None
    most_expensive: Device | None = None
    by_type: Counter[str] = Counter()
    by_manufacturer: Counter[str] = Counter()

    for device in devices:
        count += 1
        total += device.cost
        by_type[device.device_type] += 1
        by_manufacturer[device.manufacturer] += 1

        if minimum is None or device.cost < minimum:
            minimum = device.cost

        if maximum is None or device.cost > maximum:
            maximum = device.cost
            most_expensive = device

    return StreamStatistics(
        count=count,
        total_cost=total,
        average_cost=total / count if count else 0.0,
        minimum_cost=minimum,
        maximum_cost=maximum,
        most_expensive=most_expensive,
        by_type=dict(by_type),
        by_manufacturer=dict(by_manufacturer),
    )
