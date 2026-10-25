"""CRUD through the service layer and repositories (SQLAlchemy + SQLite)."""

import math

import pytest
from sqlalchemy.orm import Session, sessionmaker

from equipment_manager.exceptions import InvalidDeviceError
from equipment_manager.models import Device
from equipment_manager.persistence.exceptions import (
    ManufacturerInUseError,
    RecordNotFoundError,
)
from equipment_manager.persistence.models import DeviceModel
from equipment_manager.persistence.repositories import (
    DeviceRepository,
    ManufacturerRepository,
)
from equipment_manager.persistence.services import EquipmentService

pytestmark = pytest.mark.integration


# ----- Create ---------------------------------------------------------------


def test_create_assigns_id_and_creates_manufacturer(
    service: EquipmentService, laptop: Device
) -> None:
    created = service.register_device(laptop, location="Room 5")

    assert created.id is not None
    assert created.inventory_number == "PC-100"
    assert created.manufacturer.name == "Acer"
    assert created.location == "Room 5"
    assert created.full_name == "Acer Swift 3"


def test_created_device_is_committed_and_visible_to_another_session(
    service: EquipmentService,
    session_factory: sessionmaker[Session],
    laptop: Device,
) -> None:
    service.register_device(laptop)

    with session_factory() as other:
        found = DeviceRepository(other).get_by_inventory_number("PC-100")

    assert found is not None
    assert found.model == "Swift 3"


def test_devices_of_one_manufacturer_share_one_row(
    service: EquipmentService,
) -> None:
    service.register_device(Device("PC-101", "Laptop", "Acer", "A", 1.0))
    service.register_device(Device("PC-102", "Monitor", "ACER", "B", 2.0))

    manufacturers = service.manufacturers.get_all()

    assert [m.name for m in manufacturers] == ["Acer"]
    assert len(manufacturers[0].devices) == 2


def test_inventory_number_is_trimmed(service: EquipmentService) -> None:
    created = service.register_device(Device(" PC-7 ", "Laptop", "Acer", "A", 1.0))

    assert created.inventory_number == "PC-7"


# ----- Read -----------------------------------------------------------------


def test_read_by_inventory_number_ignores_case(seeded: EquipmentService) -> None:
    assert seeded.get_device("pc-003").model == "U2723QE"


def test_read_missing_device_raises(service: EquipmentService) -> None:
    with pytest.raises(RecordNotFoundError, match="PC-404"):
        service.get_device("PC-404")


def test_read_by_id_and_unknown_id(seeded: EquipmentService) -> None:
    first = seeded.get_device("PC-001")

    assert seeded.devices.get_by_id(first.id) is first
    assert seeded.devices.get_by_id(99999) is None


def test_list_devices_is_sorted_by_inventory_number(
    seeded: EquipmentService,
) -> None:
    numbers = [device.inventory_number for device in seeded.list_devices()]

    assert len(numbers) == 12
    assert numbers == sorted(numbers)


# ----- Update ---------------------------------------------------------------


def test_change_cost_is_persisted(
    seeded: EquipmentService, session_factory: sessionmaker[Session]
) -> None:
    seeded.change_cost("PC-001", 30000.0)

    with session_factory() as other:
        stored = DeviceRepository(other).get_by_inventory_number("PC-001")

    assert stored is not None
    assert stored.cost == 30000.0


@pytest.mark.parametrize("bad_cost", [-1.0, math.nan, math.inf])
def test_change_cost_rejects_invalid_values(
    seeded: EquipmentService, bad_cost: float
) -> None:
    with pytest.raises(InvalidDeviceError):
        seeded.change_cost("PC-001", bad_cost)

    assert seeded.get_device("PC-001").cost == 28500.0


def test_change_cost_of_missing_device_raises(service: EquipmentService) -> None:
    with pytest.raises(RecordNotFoundError):
        service.change_cost("PC-404", 10.0)


def test_change_location_sets_and_clears_value(seeded: EquipmentService) -> None:
    assert seeded.change_location("PC-002", "  Room 101 ").location == "Room 101"
    assert seeded.change_location("PC-002", None).location is None


# ----- Delete ---------------------------------------------------------------


def test_delete_removes_the_row(seeded: EquipmentService) -> None:
    seeded.remove_device("PC-012")

    assert seeded.devices.count() == 11

    with pytest.raises(RecordNotFoundError):
        seeded.get_device("PC-012")


def test_delete_missing_device_raises(service: EquipmentService) -> None:
    with pytest.raises(RecordNotFoundError):
        service.remove_device("PC-404")


def test_repository_delete_returns_false_for_unknown_id(session: Session) -> None:
    assert DeviceRepository(session).delete(99999) is False


# ----- Manufacturer repository ----------------------------------------------


def test_manufacturer_crud(session: Session) -> None:
    repository = ManufacturerRepository(session)

    created = repository.add("  Dell ")
    assert created.name == "Dell"
    assert repository.get_by_id(created.id) is created
    assert repository.get_by_name("dell") is created

    repository.rename(created.id, "Dell Technologies")
    assert repository.get_by_name("Dell Technologies") is created
    assert repository.get_by_name("Dell") is None

    assert repository.delete(created.id) is True
    assert repository.get_all() == []


def test_manufacturer_unknown_id(session: Session) -> None:
    repository = ManufacturerRepository(session)

    assert repository.delete(99999) is False

    with pytest.raises(RecordNotFoundError):
        repository.rename(99999, "Nobody")


def test_manufacturer_with_devices_cannot_be_deleted(
    seeded: EquipmentService,
) -> None:
    dell = seeded.manufacturers.get_by_name("Dell")
    assert dell is not None

    with pytest.raises(ManufacturerInUseError, match="3 device"):
        seeded.manufacturers.delete(dell.id)

    assert seeded.manufacturers.get_by_name("Dell") is not None


def test_relationship_both_directions(seeded: EquipmentService) -> None:
    device = seeded.get_device("PC-008")

    assert device.manufacturer.name == "HP"
    assert device in device.manufacturer.devices
    assert {d.inventory_number for d in device.manufacturer.devices} == {
        "PC-004",
        "PC-008",
        "PC-009",
    }


def test_models_have_readable_repr(seeded: EquipmentService) -> None:
    device = seeded.get_device("PC-001")

    assert "PC-001" in repr(device)
    assert "Lenovo" in repr(device.manufacturer)


def test_device_without_session_changes_is_not_stored(session: Session) -> None:
    """add() only flushes: without commit the row is not durable."""
    manufacturer = ManufacturerRepository(session).add("Temp")
    DeviceRepository(session).add(
        DeviceModel(
            inventory_number="TMP-1",
            device_type="Laptop",
            model="X",
            cost=1.0,
            manufacturer=manufacturer,
        )
    )
    session.rollback()

    assert DeviceRepository(session).get_by_inventory_number("TMP-1") is None
