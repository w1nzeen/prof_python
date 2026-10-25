"""Transactions: commit, rollback and the four ACID properties."""

import math
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from equipment_manager.exceptions import DuplicateDeviceError
from equipment_manager.models import Device
from equipment_manager.persistence.database import (
    create_db_engine,
    create_session_factory,
    sqlite_url,
)
from equipment_manager.persistence.exceptions import PersistenceError
from equipment_manager.persistence.models import DeviceModel
from equipment_manager.persistence.repositories import (
    DeviceRepository,
    ManufacturerRepository,
)
from equipment_manager.persistence.services import EquipmentService

pytestmark = pytest.mark.integration


def stored_numbers(session_factory: sessionmaker[Session]) -> set[str]:
    """Read the committed state through a brand-new session."""
    with session_factory() as other:
        return {d.inventory_number for d in DeviceRepository(other).get_all()}


def manufacturer_names(session_factory: sessionmaker[Session]) -> set[str]:
    with session_factory() as other:
        return {m.name for m in ManufacturerRepository(other).get_all()}


# ----- Atomicity ---------------------------------------------------------------


def test_batch_commits_every_device(
    service: EquipmentService, session_factory: sessionmaker[Session]
) -> None:
    batch = [
        Device("PC-201", "Laptop", "Acer", "A", 1.0),
        Device("PC-202", "Monitor", "Acer", "B", 2.0),
        Device("PC-203", "Router", "TP-Link", "C", 3.0),
    ]

    created = service.register_devices_batch(batch)

    assert len(created) == 3
    assert stored_numbers(session_factory) == {"PC-201", "PC-202", "PC-203"}


def test_batch_with_a_duplicate_of_stored_device_is_rolled_back(
    seeded: EquipmentService, session_factory: sessionmaker[Session]
) -> None:
    before = stored_numbers(session_factory)
    batch = [
        Device("PC-300", "Laptop", "Acer", "Swift", 1.0),
        Device("PC-301", "Laptop", "Acer", "Swift", 1.0),
        Device("PC-001", "Laptop", "Acer", "Duplicate", 1.0),
    ]

    with pytest.raises(DuplicateDeviceError):
        seeded.register_devices_batch(batch)

    assert stored_numbers(session_factory) == before
    assert "Acer" not in manufacturer_names(session_factory)


def test_batch_with_a_duplicate_inside_itself_is_rolled_back(
    service: EquipmentService, session_factory: sessionmaker[Session]
) -> None:
    batch = [
        Device("PC-400", "Laptop", "Acer", "A", 1.0),
        Device("pc-400", "Laptop", "Acer", "B", 2.0),
    ]

    with pytest.raises(DuplicateDeviceError):
        service.register_devices_batch(batch)

    assert stored_numbers(session_factory) == set()
    assert manufacturer_names(session_factory) == set()


def test_batch_is_rolled_back_when_the_database_rejects_a_row(
    service: EquipmentService, session_factory: sessionmaker[Session]
) -> None:
    """NaN is stored by SQLite as NULL, which violates NOT NULL."""
    batch = [
        Device("PC-500", "Laptop", "Acer", "A", 1.0),
        Device("PC-501", "Laptop", "Acer", "B", math.nan),
    ]

    with pytest.raises(PersistenceError):
        service.register_devices_batch(batch)

    assert stored_numbers(session_factory) == set()


def test_failed_update_leaves_the_old_value(seeded: EquipmentService) -> None:
    with pytest.raises(DuplicateDeviceError), seeded.transaction():
        seeded.get_device("PC-001").cost = 1.0
        seeded.devices.add(
            DeviceModel(
                inventory_number="PC-002",  # duplicate -> error
                device_type="Laptop",
                model="X",
                cost=1.0,
                manufacturer_id=1,
            )
        )

    assert seeded.get_device("PC-001").cost == 28500.0


# ----- Consistency ---------------------------------------------------------------


def test_session_is_usable_after_a_rollback(
    seeded: EquipmentService, laptop: Device
) -> None:
    with pytest.raises(DuplicateDeviceError):
        seeded.register_devices_batch([laptop, Device("PC-001", "X", "Acer", "Y", 1.0)])

    seeded.register_device(laptop)

    assert seeded.devices.count() == 13
    assert seeded.manufacturers.get_by_name("Acer") is not None


def test_totals_stay_correct_after_failed_and_successful_operations(
    seeded: EquipmentService,
) -> None:
    total = seeded.statistics().total_cost

    with pytest.raises(DuplicateDeviceError):
        seeded.register_devices_batch(
            [Device("PC-600", "Laptop", "Acer", "A", 999.0), Device("PC-001", "L", "A", "M", 1.0)]
        )

    assert seeded.statistics().total_cost == pytest.approx(total)

    seeded.register_device(Device("PC-600", "Laptop", "Acer", "A", 999.0))

    assert seeded.statistics().total_cost == pytest.approx(total + 999.0)


# ----- Isolation -------------------------------------------------------------


def test_uncommitted_changes_are_invisible_to_other_sessions(
    session: Session, session_factory: sessionmaker[Session]
) -> None:
    ManufacturerRepository(session).add("Pending")  # flushed, not committed

    assert "Pending" not in manufacturer_names(session_factory)

    session.commit()

    assert "Pending" in manufacturer_names(session_factory)


def test_explicit_rollback_discards_flushed_changes(
    session: Session, session_factory: sessionmaker[Session]
) -> None:
    ManufacturerRepository(session).add("Discarded")
    session.rollback()

    assert manufacturer_names(session_factory) == set()
    assert ManufacturerRepository(session).get_by_name("Discarded") is None


# ----- Durability ---------------------------------------------------------------


def test_committed_data_survives_a_new_engine(
    service: EquipmentService, engine: Engine, db_path: Path, laptop: Device
) -> None:
    service.register_device(laptop)
    service.session.close()
    engine.dispose()  # drop every connection: only the file remains

    reopened = create_db_engine(sqlite_url(db_path))
    try:
        with create_session_factory(reopened)() as session:
            found = DeviceRepository(session).get_by_inventory_number("PC-100")

        assert found is not None
        assert found.cost == 25000.0
    finally:
        reopened.dispose()
