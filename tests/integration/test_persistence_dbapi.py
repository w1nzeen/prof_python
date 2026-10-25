"""Plain DB-API (sqlite3): parameterized queries, commit and rollback."""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from equipment_manager.persistence import dbapi
from equipment_manager.persistence.repositories import DeviceRepository
from equipment_manager.persistence.services import EquipmentService

pytestmark = pytest.mark.integration


def test_search_by_manufacturer(seeded: EquipmentService, db_path: Path) -> None:
    rows = dbapi.search_devices(db_path, manufacturer="hp")

    assert [row.inventory_number for row in rows] == ["PC-004", "PC-008", "PC-009"]
    assert rows[1] == dbapi.DeviceRow(
        "PC-008", "Server", "HP", "ProLiant DL20", 74500.0
    )


def test_search_by_inventory_number_ignores_case(
    seeded: EquipmentService, db_path: Path
) -> None:
    rows = dbapi.search_devices(db_path, inventory_number="pc-003")

    assert [row.model for row in rows] == ["U2723QE"]


def test_search_by_both_filters(seeded: EquipmentService, db_path: Path) -> None:
    assert len(dbapi.search_devices(db_path, inventory_number="PC-004", manufacturer="HP")) == 1
    assert dbapi.search_devices(db_path, inventory_number="PC-004", manufacturer="Dell") == []


def test_search_without_filters_returns_everything(
    seeded: EquipmentService, db_path: Path
) -> None:
    assert len(dbapi.search_devices(db_path)) == 12


def test_dbapi_and_orm_see_the_same_rows(
    seeded: EquipmentService, db_path: Path
) -> None:
    orm = [d.inventory_number for d in seeded.filter_by_manufacturer("Lenovo")]
    raw = [r.inventory_number for r in dbapi.search_devices(db_path, manufacturer="Lenovo")]

    assert raw == orm


@pytest.mark.parametrize(
    "hostile",
    [
        "x' OR '1'='1",
        "HP' --",
        "'; DROP TABLE devices; --",
        "HP%",
    ],
)
def test_parameterized_query_is_not_vulnerable_to_sql_injection(
    seeded: EquipmentService, db_path: Path, hostile: str
) -> None:
    assert dbapi.search_devices(db_path, manufacturer=hostile) == []
    assert dbapi.search_devices(db_path, inventory_number=hostile) == []
    assert len(dbapi.search_devices(db_path)) == 12  # table is still there


def test_update_cost_commits_and_is_visible_through_the_orm(
    seeded: EquipmentService,
    db_path: Path,
    session_factory: sessionmaker[Session],
) -> None:
    assert dbapi.update_cost(db_path, "PC-001", 31000.0) is True

    with session_factory() as other:
        device = DeviceRepository(other).get_by_inventory_number("PC-001")

    assert device is not None
    assert device.cost == 31000.0


def test_update_cost_of_unknown_device_returns_false(
    seeded: EquipmentService, db_path: Path
) -> None:
    assert dbapi.update_cost(db_path, "PC-404", 1.0) is False


def test_update_cost_rolls_back_on_constraint_violation(
    seeded: EquipmentService, db_path: Path
) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        dbapi.update_cost(db_path, "PC-001", -5.0)

    assert dbapi.search_devices(db_path, inventory_number="PC-001")[0].cost == 28500.0
