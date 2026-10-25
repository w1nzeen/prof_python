"""Database constraints: UNIQUE, CHECK, FOREIGN KEY, NOT NULL."""

from pathlib import Path

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from equipment_manager.exceptions import DuplicateDeviceError, InvalidDeviceError
from equipment_manager.models import Device
from equipment_manager.persistence.database import (
    DATABASE_URL_VARIABLE,
    create_db_engine,
    init_db,
    sqlite_url,
)
from equipment_manager.persistence.exceptions import (
    DuplicateManufacturerError,
    PersistenceError,
    ReferenceIntegrityError,
)
from equipment_manager.persistence.models import DeviceModel
from equipment_manager.persistence.repositories import (
    DeviceRepository,
    ManufacturerRepository,
)
from equipment_manager.persistence.services import EquipmentService

pytestmark = pytest.mark.integration


def make_row(**overrides: object) -> DeviceModel:
    values: dict[str, object] = {
        "inventory_number": "PC-900",
        "device_type": "Laptop",
        "model": "Test",
        "cost": 10.0,
        "manufacturer_id": 1,
    }
    values.update(overrides)

    return DeviceModel(**values)


# ----- UNIQUE ----------------------------------------------------------------


def test_service_rejects_duplicate_inventory_number(
    seeded: EquipmentService,
) -> None:
    with pytest.raises(DuplicateDeviceError, match="PC-001"):
        seeded.register_device(Device("PC-001", "Laptop", "Dell", "XPS", 1.0))

    assert seeded.devices.count() == 12


def test_inventory_number_is_unique_ignoring_case(seeded: EquipmentService) -> None:
    with pytest.raises(DuplicateDeviceError):
        seeded.register_device(Device("pc-001", "Laptop", "Dell", "XPS", 1.0))


def test_unique_constraint_works_without_the_service_check(
    seeded: EquipmentService, session: Session
) -> None:
    """The database itself guards the rule, not only the Python code."""
    with pytest.raises(DuplicateDeviceError):
        DeviceRepository(session).add(make_row(inventory_number="PC-002"))


def test_duplicate_manufacturer_name_is_rejected(seeded: EquipmentService) -> None:
    with pytest.raises(DuplicateManufacturerError):
        ManufacturerRepository(seeded.session).add("dell")


# ----- CHECK / NOT NULL / FOREIGN KEY -------------------------------------


def test_negative_cost_violates_check_constraint(
    seeded: EquipmentService, session: Session
) -> None:
    with pytest.raises(InvalidDeviceError, match="negative"):
        DeviceRepository(session).add(make_row(cost=-1.0))


def test_not_null_violation_becomes_a_persistence_error(
    seeded: EquipmentService, session: Session
) -> None:
    with pytest.raises(PersistenceError, match="NOT NULL"):
        DeviceRepository(session).add(make_row(model=None))


def test_foreign_key_to_unknown_manufacturer_is_rejected(
    seeded: EquipmentService, session: Session
) -> None:
    with pytest.raises(ReferenceIntegrityError):
        DeviceRepository(session).add(make_row(manufacturer_id=999))


def test_foreign_keys_are_enabled_on_every_connection(engine: Engine) -> None:
    with engine.connect() as connection:
        enabled = connection.execute(text("PRAGMA foreign_keys")).scalar_one()

    assert enabled == 1


def test_database_rejects_row_deletion_that_breaks_a_foreign_key(
    seeded: EquipmentService, session: Session
) -> None:
    """ON DELETE RESTRICT also works for raw SQL, bypassing the ORM."""
    with pytest.raises(Exception, match="FOREIGN KEY"):
        session.execute(text("DELETE FROM manufacturers WHERE name = 'Dell'"))


# ----- configuration ----------------------------------------------------------


def test_engine_url_comes_from_the_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database = tmp_path / "from_env.db"
    monkeypatch.setenv(
        DATABASE_URL_VARIABLE, sqlite_url(database).render_as_string(False)
    )

    engine = create_db_engine()
    init_db(engine)
    init_db(engine)  # create_all is idempotent
    engine.dispose()

    assert database.exists()
