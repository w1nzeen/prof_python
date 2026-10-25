"""Unit tests of InventoryRegistry: registration, search, filters, statistics."""

from collections.abc import Callable

import pytest

from equipment_manager.domain.exceptions import (
    DeviceNotFoundError,
    DuplicateKeyError,
    InvalidValueError,
)
from equipment_manager.domain.models import (
    Computer,
    Device,
    DeviceStatus,
    InventoryRegistry,
    Printer,
)
from equipment_manager.domain.value_objects import InventoryNumber, Money

DeviceFactory = Callable[..., Device]


# ----------------------------------------------------------- registration
def test_new_registry_is_empty(registry: InventoryRegistry) -> None:
    assert len(registry) == 0
    assert list(registry) == []
    assert "PC-001" not in registry


def test_register_adds_device(registry: InventoryRegistry, computer: Computer) -> None:
    registry.register(computer)

    assert len(registry) == 1
    assert computer in list(registry)
    assert "PC-001" in registry


def test_registering_same_number_twice_is_rejected(
    registry: InventoryRegistry, device_factory: DeviceFactory
) -> None:
    registry.register(device_factory(inventory_number="PC-010"))

    with pytest.raises(DuplicateKeyError, match="already exists"):
        registry.register(device_factory(inventory_number="PC-010", model="Other"))

    assert len(registry) == 1


def test_unregister_is_idempotent(populated_registry: InventoryRegistry) -> None:
    assert populated_registry.unregister("PC-003") is True
    assert populated_registry.unregister("PC-003") is False
    assert len(populated_registry) == 2


# ----------------------------------------------------------------- search
@pytest.mark.parametrize("number", ["PC-001", "pc-001", " PC-001 "])
def test_find_normalizes_inventory_number(
    populated_registry: InventoryRegistry, number: str
) -> None:
    found = populated_registry.find(number)

    assert found is not None
    assert str(found.inventory_number) == "PC-001"


def test_find_accepts_value_object(populated_registry: InventoryRegistry) -> None:
    assert populated_registry.find(InventoryNumber("PC-004")) is not None


def test_find_returns_none_for_unknown_number(
    populated_registry: InventoryRegistry,
) -> None:
    assert populated_registry.find("PC-999") is None


def test_find_with_malformed_number_raises(
    populated_registry: InventoryRegistry,
) -> None:
    with pytest.raises(InvalidValueError):
        populated_registry.find("not a number")


def test_getitem_raises_for_missing_device(
    populated_registry: InventoryRegistry,
) -> None:
    with pytest.raises(DeviceNotFoundError, match="PC-999"):
        _ = populated_registry["PC-999"]


@pytest.mark.parametrize("item", ["bad", 5, None, 1.5])
def test_contains_is_false_for_unusable_keys(
    populated_registry: InventoryRegistry, item: object
) -> None:
    assert (item in populated_registry) is False


# ---------------------------------------------------------------- filters
@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Lenovo", ["PC-001"]),
        ("lenovo", ["PC-001"]),
        (" HP ", ["PC-004"]),
        ("Dell", ["PC-003"]),
        ("Apple", []),
        ("", []),
    ],
)
def test_filter_by_manufacturer(
    populated_registry: InventoryRegistry, name: str, expected: list[str]
) -> None:
    result = populated_registry.by_manufacturer(name)

    assert [str(d.inventory_number) for d in result] == expected


def test_filter_by_type_keeps_precise_type(
    populated_registry: InventoryRegistry,
) -> None:
    computers = populated_registry.by_type(Computer)
    printers = populated_registry.by_type(Printer)

    assert [type(d) for d in computers] == [Computer]
    assert [type(d) for d in printers] == [Printer]
    assert len(populated_registry.by_type(Device)) == 3


def test_filter_by_status(
    populated_registry: InventoryRegistry, computer: Computer
) -> None:
    computer.change_status(DeviceStatus.IN_REPAIR)

    assert populated_registry.by_status(DeviceStatus.IN_REPAIR) == [computer]
    assert len(populated_registry.by_status(DeviceStatus.IN_USE)) == 2
    assert populated_registry.by_status(DeviceStatus.DECOMMISSIONED) == []


def test_counts_by_manufacturer_and_kind(
    populated_registry: InventoryRegistry,
) -> None:
    assert populated_registry.count_by_manufacturer() == {
        "Lenovo": 1, "HP": 1, "Dell": 1,
    }
    assert populated_registry.count_by_kind() == {
        "Computer": 1, "Printer": 1, "Device": 1,
    }


# ------------------------------------------------------------- statistics
def test_total_cost(populated_registry: InventoryRegistry) -> None:
    assert populated_registry.total_cost() == Money.of("50500.50")


def test_average_cost(populated_registry: InventoryRegistry) -> None:
    average = populated_registry.average_cost()

    assert float(average.amount) == pytest.approx(16833.50)


def test_average_cost_is_rounded_to_cents(
    registry: InventoryRegistry, device_factory: DeviceFactory
) -> None:
    for number, cost in (("PC-001", 10), ("PC-002", 10), ("PC-003", 11)):
        registry.register(device_factory(inventory_number=number, cost=cost))

    assert registry.average_cost() == Money.of("10.33")


def test_most_expensive_device(populated_registry: InventoryRegistry) -> None:
    best = populated_registry.most_expensive()

    assert best is not None
    assert str(best.inventory_number) == "PC-001"


def test_most_expensive_returns_first_of_equal_costs(
    registry: InventoryRegistry, device_factory: DeviceFactory
) -> None:
    registry.register(device_factory(inventory_number="PC-001", cost=500))
    registry.register(device_factory(inventory_number="PC-002", cost=500))

    best = registry.most_expensive()

    assert best is not None
    assert str(best.inventory_number) == "PC-001"


def test_empty_registry_statistics(registry: InventoryRegistry) -> None:
    assert registry.total_cost() == Money.zero()
    assert registry.average_cost() == Money.zero()
    assert registry.most_expensive() is None
    assert registry.count_by_manufacturer() == {}
    assert registry.count_by_kind() == {}


def test_zero_cost_devices_are_valid(
    registry: InventoryRegistry, device_factory: DeviceFactory
) -> None:
    registry.register(device_factory(inventory_number="PC-001", cost=0))

    assert registry.total_cost() == Money.zero()
    assert registry.average_cost() == Money.zero()


def test_statistics_in_other_currency(
    registry: InventoryRegistry,
    device_factory: DeviceFactory,
    currency: str,
) -> None:
    device = device_factory(inventory_number="PC-001")
    device.cost = Money.of(100, "UAH")
    registry.register(device)

    if currency == "UAH":
        assert registry.total_cost(currency) == Money.of(100)
    else:
        from equipment_manager.domain.exceptions import CurrencyMismatchError

        with pytest.raises(CurrencyMismatchError):
            registry.total_cost(currency)


def test_repeated_statistics_do_not_change_state(
    populated_registry: InventoryRegistry,
) -> None:
    first = populated_registry.total_cost()
    second = populated_registry.total_cost()

    assert first == second
    assert len(populated_registry) == 3
