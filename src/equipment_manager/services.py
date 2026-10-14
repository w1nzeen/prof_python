"""Business logic of the equipment manager."""

from equipment_manager.exceptions import DuplicateDeviceError
from equipment_manager.models import Device


def add_device(devices: list[Device], device: Device) -> None:
    """Add a device; inventory numbers must be unique."""
    if find_device(devices, device.inventory_number) is not None:
        raise DuplicateDeviceError(
            f"Device {device.inventory_number} already exists."
        )

    devices.append(device)


def find_device(
    devices: list[Device],
    inventory_number: str,
) -> Device | None:
    """Find a device by its exact inventory number."""
    for device in devices:
        if device.inventory_number.lower() == inventory_number.strip().lower():
            return device

    return None


def search_devices(devices: list[Device], query: str) -> list[Device]:
    """Search by part of inventory number, type, manufacturer or model."""
    text = query.strip().lower()

    return [
        device
        for device in devices
        if text in device.inventory_number.lower()
        or text in device.device_type.lower()
        or text in device.manufacturer.lower()
        or text in device.model.lower()
    ]


def filter_by_manufacturer(
    devices: list[Device],
    manufacturer: str,
) -> list[Device]:
    """Return devices of the given manufacturer (case-insensitive)."""
    return [
        device
        for device in devices
        if device.manufacturer.lower() == manufacturer.strip().lower()
    ]


def calculate_average_cost(devices: list[Device]) -> float:
    """Average cost of devices; 0.0 for an empty list."""
    if not devices:
        return 0.0

    return calculate_total_cost(devices) / len(devices)


def find_most_expensive(devices: list[Device]) -> Device | None:
    """Return the most expensive device or None for an empty list."""
    if not devices:
        return None

    return max(devices, key=lambda device: device.cost)


def calculate_total_cost(devices: list[Device]) -> float:
    """Total cost of all devices."""
    return sum(device.cost for device in devices)
