"""Functions that select, group and index devices."""

from collections import Counter, defaultdict
from collections.abc import Callable
from functools import reduce

from equipment_manager.decorators import OPERATION_HISTORY, record_operation
from equipment_manager.models import Device

Predicate = Callable[[Device], bool]
KeyFunc = Callable[[Device], str]
Step = Callable[[list[Device]], list[Device]]


def get_unique_manufacturers(devices: list[Device]) -> set[str]:
    """set comprehension: unique manufacturers, O(n)."""
    return {device.manufacturer for device in devices}


def get_unique_types(devices: list[Device]) -> set[str]:
    return {device.device_type for device in devices}


def create_device_index(devices: list[Device]) -> dict[str, Device]:
    """dict comprehension: inventory number -> device, O(n)."""
    return {device.inventory_number: device for device in devices}


def find_by_inventory_number(
    index: dict[str, Device],
    inventory_number: str,
) -> Device | None:
    """Search in the dict index, O(1) on average."""
    return index.get(inventory_number)


def find_linear(
    devices: list[Device],
    inventory_number: str,
) -> Device | None:
    """Search in the list, O(n). Used for the benchmark."""
    for device in devices:
        if device.inventory_number == inventory_number:
            return device

    return None


def filter_items(
    devices: list[Device],
    predicate: Predicate,
) -> list[Device]:
    """Universal filter: keeps devices for which predicate is True."""
    return [device for device in devices if predicate(device)]


@record_operation(OPERATION_HISTORY)
def filter_by_manufacturer(
    devices: list[Device],
    manufacturer: str,
) -> list[Device]:
    """list comprehension: devices of one manufacturer, O(n)."""
    name = manufacturer.strip().lower()

    return [
        device
        for device in devices
        if device.manufacturer.lower() == name
    ]


def group_by(devices: list[Device], key: KeyFunc) -> dict[str, list[Device]]:
    """Universal grouping with defaultdict, O(n)."""
    result: defaultdict[str, list[Device]] = defaultdict(list)

    for device in devices:
        result[key(device)].append(device)

    return dict(result)


@record_operation(OPERATION_HISTORY)
def group_by_manufacturer(
    devices: list[Device],
) -> dict[str, list[Device]]:
    return group_by(devices, lambda device: device.manufacturer)


@record_operation(OPERATION_HISTORY)
def group_by_type(devices: list[Device]) -> dict[str, list[Device]]:
    return group_by(devices, lambda device: device.device_type)


def group_by_type_and_manufacturer(
    devices: list[Device],
) -> dict[str, dict[str, list[Device]]]:
    """Nested grouping: type -> manufacturer -> devices."""
    return {
        device_type: group_by(items, lambda device: device.manufacturer)
        for device_type, items in group_by_type(devices).items()
    }


@record_operation(OPERATION_HISTORY)
def count_by_type(devices: list[Device]) -> Counter[str]:
    """Counter of device types, O(n)."""
    return Counter(device.device_type for device in devices)


def process_pipeline(devices: list[Device], *steps: Step) -> list[Device]:
    """Apply processing steps one after another (*args)."""
    return reduce(lambda current, step: step(current), steps, devices)
