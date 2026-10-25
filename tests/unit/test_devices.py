"""Unit tests of Device, Computer and Printer."""

from collections.abc import Callable
from datetime import date

import pytest

from equipment_manager.domain.exceptions import (
    InvalidStatusTransitionError,
    InvalidValueError,
    MaintenanceError,
)
from equipment_manager.domain.models import (
    ALLOWED_TRANSITIONS,
    Computer,
    Device,
    DeviceStatus,
    MaintenanceRecord,
    Manufacturer,
    Printer,
    PrintTechnology,
)
from equipment_manager.domain.value_objects import InventoryNumber, Money

DeviceFactory = Callable[..., Device]


def test_computer_is_created_with_specifications(computer: Computer) -> None:
    assert isinstance(computer, Device)
    assert computer.kind == "Computer"
    assert computer.specifications() == {
        "CPU": "Intel Core i5",
        "RAM": "16 GB",
        "Storage": "512 GB",
    }
    assert computer.status is DeviceStatus.IN_USE


def test_printer_is_created_with_specifications(printer: Printer) -> None:
    assert printer.kind == "Printer"
    assert printer.specifications() == {"Technology": "laser", "Speed": "20 ppm"}


def test_generic_device_has_no_specifications(monitor: Device) -> None:
    assert monitor.kind == "Device"
    assert monitor.specifications() == {}
    assert monitor.full_name == "Dell U2723QE"


def test_str_and_repr_contain_identity(computer: Computer) -> None:
    assert str(computer) == "PC-001 Computer: Lenovo ThinkPad E14 (28500.00 UAH)"
    assert repr(computer).startswith("Computer(inventory_number='PC-001'")


def test_devices_with_same_inventory_number_are_equal(
    device_factory: DeviceFactory,
) -> None:
    first = device_factory("computer", inventory_number="PC-007")
    second = device_factory("printer", inventory_number="PC-007")

    assert first == second
    assert len({first, second}) == 1
    assert first != "PC-007"


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"model": ""}, id="empty-model"),
        pytest.param({"model": "   "}, id="blank-model"),
    ],
)
def test_empty_model_is_rejected(
    device_factory: DeviceFactory, overrides: dict[str, str]
) -> None:
    with pytest.raises(InvalidValueError, match="Model"):
        device_factory("computer", **overrides)


@pytest.mark.parametrize(
    ("ram", "storage"),
    [(0, 512), (16, 0), (-1, 512), (16, -1)],
)
def test_computer_requires_positive_memory(
    device_factory: DeviceFactory, ram: int, storage: int
) -> None:
    with pytest.raises(InvalidValueError, match="positive"):
        device_factory("computer", ram_gb=ram, storage_gb=storage)


@pytest.mark.parametrize("speed", [0, -5])
def test_printer_requires_positive_speed(
    device_factory: DeviceFactory, speed: int
) -> None:
    with pytest.raises(InvalidValueError, match="positive"):
        device_factory("printer", pages_per_minute=speed)


def test_manufacturer_requires_name() -> None:
    with pytest.raises(InvalidValueError, match="name"):
        Manufacturer("   ")

    assert Manufacturer("  Dell ").name == "Dell"


@pytest.mark.parametrize(
    ("name", "expected"),
    [("dell", True), ("DELL", True), (" Dell ", True), ("HP", False)],
)
def test_manufacturer_matching_ignores_case(name: str, expected: bool) -> None:
    assert Manufacturer("Dell").matches(name) is expected


def test_inventory_number_is_read_only(computer: Computer) -> None:
    with pytest.raises(AttributeError):
        computer.inventory_number = InventoryNumber("PC-999")  # type: ignore[misc]


def test_cost_can_be_changed_within_the_same_currency(computer: Computer) -> None:
    computer.cost = Money.of(30000)

    assert computer.cost == Money.of(30000)


def test_cost_currency_cannot_change(computer: Computer) -> None:
    with pytest.raises(InvalidValueError, match="Currency"):
        computer.cost = Money.of(100, "USD")

    assert computer.cost == Money.of(28500)


# ---------------------------------------------------------------- status
ALL_STATUSES = list(DeviceStatus)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        pytest.param(current, target, id=f"{current.value}->{target.value}")
        for current in ALL_STATUSES
        for target in ALL_STATUSES
        if target in ALLOWED_TRANSITIONS[current]
    ],
)
def test_allowed_status_transitions(
    device_factory: DeviceFactory, current: DeviceStatus, target: DeviceStatus
) -> None:
    device = device_factory("computer", status=current)

    device.change_status(target)

    assert device.status is target


@pytest.mark.parametrize(
    ("current", "target"),
    [
        pytest.param(current, target, id=f"{current.value}->{target.value}")
        for current in ALL_STATUSES
        for target in ALL_STATUSES
        if target not in ALLOWED_TRANSITIONS[current]
    ],
)
def test_forbidden_status_transitions(
    device_factory: DeviceFactory, current: DeviceStatus, target: DeviceStatus
) -> None:
    device = device_factory("computer", status=current)

    with pytest.raises(InvalidStatusTransitionError, match="Cannot change status"):
        device.change_status(target)

    assert device.status is current


def test_decommissioned_is_terminal(device_factory: DeviceFactory) -> None:
    device = device_factory("computer")
    device.change_status(DeviceStatus.DECOMMISSIONED)

    for status in DeviceStatus:
        with pytest.raises(InvalidStatusTransitionError):
            device.change_status(status)


def test_unknown_status_value_is_rejected(device_factory: DeviceFactory) -> None:
    with pytest.raises(ValueError):
        device_factory("computer", status="lost")


def test_status_is_a_string_enum() -> None:
    assert DeviceStatus("in_repair") is DeviceStatus.IN_REPAIR
    status: object = DeviceStatus.IN_USE

    assert status == "in_use"


# ----------------------------------------------------------- maintenance
def test_last_service_date_defaults_to_purchase_date(computer: Computer) -> None:
    assert computer.maintenance_history == ()
    assert computer.last_service_date == date(2025, 1, 15)


def test_maintenance_records_are_kept_in_order(computer: Computer) -> None:
    first = MaintenanceRecord(date(2025, 6, 1), "Cleaning")
    second = MaintenanceRecord(date(2025, 12, 1), "Thermal paste", "I. Koval")

    computer.record_maintenance(first)
    computer.record_maintenance(second)

    assert computer.maintenance_history == (first, second)
    assert computer.last_service_date == date(2025, 12, 1)


def test_maintenance_history_snapshot_does_not_change(computer: Computer) -> None:
    before = computer.maintenance_history

    computer.record_maintenance(MaintenanceRecord(date(2025, 6, 1), "Cleaning"))

    assert before == ()
    assert len(computer.maintenance_history) == 1


def test_maintenance_cannot_precede_purchase(computer: Computer) -> None:
    with pytest.raises(MaintenanceError, match="earlier"):
        computer.record_maintenance(MaintenanceRecord(date(2024, 1, 1), "Too early"))

    assert computer.maintenance_history == ()


def test_maintenance_on_purchase_day_is_the_boundary(computer: Computer) -> None:
    computer.record_maintenance(MaintenanceRecord(date(2025, 1, 15), "Setup"))

    assert len(computer.maintenance_history) == 1


def test_maintenance_record_requires_description() -> None:
    with pytest.raises(InvalidValueError, match="Description"):
        MaintenanceRecord(date(2025, 1, 1), "  ")


def test_print_technology_values() -> None:
    assert PrintTechnology("inkjet") is PrintTechnology.INKJET
