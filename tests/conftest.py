"""Shared fixtures of the test suite (not imported manually by tests)."""

from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import Mock, create_autospec

import pytest

from equipment_manager.domain.models import (
    Computer,
    Device,
    InventoryRegistry,
    Manufacturer,
    Printer,
    PrintTechnology,
)
from equipment_manager.domain.protocols import Notifier
from equipment_manager.domain.repositories import InMemoryRepository
from equipment_manager.domain.value_objects import InventoryNumber, Money

FIXED_TODAY = date(2026, 10, 15)

IMPORTER_ENVIRONMENT = (
    "IMPORTER_INPUT_PATH",
    "IMPORTER_OUTPUT_PATH",
    "IMPORTER_SKIP_INVALID",
    "IMPORTER_MINIMUM_VALUE",
    "IMPORTER_LOG_LEVEL",
)


@pytest.fixture(autouse=True)
def clean_importer_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """autouse: a developer's IMPORTER_* variables must not affect tests."""
    for name in IMPORTER_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def today() -> date:
    return FIXED_TODAY


DeviceFactory = Callable[..., Device]


@pytest.fixture
def device_factory() -> DeviceFactory:
    """Fixture factory: builds a device of any kind with overridable fields."""

    def create(kind: str = "computer", **overrides: Any) -> Device:
        common: dict[str, Any] = {
            "inventory_number": InventoryNumber("PC-001"),
            "manufacturer": Manufacturer("Lenovo", "China"),
            "model": "ThinkPad E14",
            "cost": Money.of(1000),
            "purchased_on": date(2025, 1, 15),
        }
        common.update(overrides)

        if isinstance(common["inventory_number"], str):
            common["inventory_number"] = InventoryNumber(common["inventory_number"])

        if isinstance(common["manufacturer"], str):
            common["manufacturer"] = Manufacturer(common["manufacturer"])

        if not isinstance(common["cost"], Money):
            common["cost"] = Money.of(common["cost"])

        if kind == "computer":
            return Computer(
                cpu=common.pop("cpu", "Intel Core i5"),
                ram_gb=common.pop("ram_gb", 16),
                storage_gb=common.pop("storage_gb", 512),
                **common,
            )

        if kind == "printer":
            return Printer(
                technology=common.pop("technology", PrintTechnology.LASER),
                pages_per_minute=common.pop("pages_per_minute", 20),
                **common,
            )

        return Device(**common)

    return create


@pytest.fixture
def computer(device_factory: DeviceFactory) -> Computer:
    device = device_factory("computer", inventory_number="PC-001", cost=28500)
    assert isinstance(device, Computer)

    return device


@pytest.fixture
def printer(device_factory: DeviceFactory) -> Printer:
    device = device_factory(
        "printer",
        inventory_number="PC-004",
        manufacturer="HP",
        model="LaserJet M111w",
        cost=4800,
    )
    assert isinstance(device, Printer)

    return device


@pytest.fixture
def monitor(device_factory: DeviceFactory) -> Device:
    return device_factory(
        "device",
        inventory_number="PC-003",
        manufacturer="Dell",
        model="U2723QE",
        cost="17200.50",
    )


@pytest.fixture
def repository() -> Iterator[InMemoryRepository[InventoryNumber, Device]]:
    """Fixture with teardown: the storage is emptied after every test."""
    storage: InMemoryRepository[InventoryNumber, Device] = InMemoryRepository(
        lambda device: device.inventory_number
    )
    yield storage

    for key in list(storage.keys()):
        storage.remove(key)


@pytest.fixture
def registry(
    repository: InMemoryRepository[InventoryNumber, Device],
) -> InventoryRegistry:
    return InventoryRegistry(repository)


@pytest.fixture
def populated_registry(
    registry: InventoryRegistry,
    computer: Computer,
    printer: Printer,
    monitor: Device,
) -> InventoryRegistry:
    for device in (computer, printer, monitor):
        registry.register(device)

    return registry


@pytest.fixture(params=["UAH", "USD", "EUR"])
def currency(request: pytest.FixtureRequest) -> str:
    """Parameterized fixture: every test using it runs for each currency."""
    return str(request.param)


@pytest.fixture
def notifier() -> Mock:
    """Mock restricted to the real Notifier interface (autospec)."""
    mock: Mock = create_autospec(Notifier, instance=True)
    return mock


class FakeRepository:
    """Working in-memory implementation of the Repository protocol."""

    def __init__(self) -> None:
        self.items: dict[InventoryNumber, Device] = {}

    def add(self, item: Device) -> None:
        self.items[item.inventory_number] = item

    def get(self, key: InventoryNumber) -> Device | None:
        return self.items.get(key)

    def remove(self, key: InventoryNumber) -> bool:
        return self.items.pop(key, None) is not None

    def all(self) -> list[Device]:
        return list(self.items.values())

    def keys(self) -> list[InventoryNumber]:
        return list(self.items)


@pytest.fixture
def fake_repository() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def csv_writer(tmp_path: Path) -> Callable[[str, str], Path]:
    """Writes a text file inside the isolated temporary directory."""

    def write(name: str, text: str) -> Path:
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")

        return path

    return write

