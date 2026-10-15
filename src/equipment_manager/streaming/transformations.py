"""Stage 5: transformation of records."""

from collections.abc import Generator, Iterable, Iterator
from dataclasses import replace
from itertools import accumulate, pairwise, tee

from equipment_manager.models import Device


def normalize_devices(
    devices: Iterable[Device],
) -> Generator[Device, None, None]:
    """Unify the format: upper-case inventory number, title-case type."""
    for device in devices:
        yield replace(
            device,
            inventory_number=device.inventory_number.upper(),
            device_type=device.device_type.title(),
        )


def describe_devices(devices: Iterable[Device]) -> Iterator[str]:
    """Short text representation of every device."""
    for device in devices:
        yield (
            f"{device.inventory_number}: {device.full_name} "
            f"[{device.device_type}] {device.cost:.2f}"
        )


def with_running_total(
    devices: Iterable[Device],
) -> Iterator[tuple[Device, float]]:
    """Pair every device with the cumulative cost (itertools.accumulate)."""
    for_costs, for_devices = tee(devices)
    totals = accumulate(device.cost for device in for_costs)

    yield from zip(for_devices, totals)


def cost_differences(devices: Iterable[Device]) -> Iterator[float]:
    """Cost change between neighbouring devices (itertools.pairwise)."""
    for previous, current in pairwise(devices):
        yield current.cost - previous.cost
