import pytest

from equipment_manager.exceptions import (
    DuplicateDeviceError,
    InvalidDeviceError,
)
from equipment_manager.models import Device
from equipment_manager.services import (
    add_device,
    calculate_average_cost,
    calculate_total_cost,
    filter_by_manufacturer,
    find_device,
    find_most_expensive,
    search_devices,
)


@pytest.fixture
def devices() -> list[Device]:
    return [
        Device("PC-001", "Laptop", "Lenovo", "ThinkPad", 1000.0),
        Device("PC-002", "Monitor", "Dell", "U2723", 500.0),
        Device("PC-003", "Laptop", "Dell", "Latitude", 1500.0),
    ]


def test_total_and_average(devices: list[Device]) -> None:
    assert calculate_total_cost(devices) == 3000.0
    assert calculate_average_cost(devices) == 1000.0


def test_empty_list() -> None:
    assert calculate_average_cost([]) == 0.0
    assert find_most_expensive([]) is None


def test_most_expensive(devices: list[Device]) -> None:
    best = find_most_expensive(devices)
    assert best is not None
    assert best.inventory_number == "PC-003"


def test_filter_by_manufacturer(devices: list[Device]) -> None:
    result = filter_by_manufacturer(devices, "dell")
    assert [d.inventory_number for d in result] == ["PC-002", "PC-003"]


def test_find_and_search(devices: list[Device]) -> None:
    assert find_device(devices, "pc-001") is not None
    assert find_device(devices, "XX") is None
    assert len(search_devices(devices, "laptop")) == 2


def test_add_duplicate(devices: list[Device]) -> None:
    with pytest.raises(DuplicateDeviceError):
        add_device(devices, Device("PC-001", "Mouse", "Logitech", "M90", 10.0))


def test_invalid_device() -> None:
    with pytest.raises(InvalidDeviceError):
        Device("PC-009", "Mouse", "Logitech", "M90", -1.0)
    with pytest.raises(InvalidDeviceError):
        Device("", "Mouse", "Logitech", "M90", 1.0)
