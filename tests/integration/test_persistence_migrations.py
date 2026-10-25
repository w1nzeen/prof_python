"""Alembic migrations on a separate temporary database."""

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from equipment_manager.persistence.database import sqlite_url

pytestmark = pytest.mark.integration

PROJECT = Path(__file__).resolve().parents[2]


@pytest.fixture
def alembic_config(db_path: Path) -> Config:
    config = Config(str(PROJECT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT / "migrations"))
    config.set_main_option(
        "sqlalchemy.url", sqlite_url(db_path).render_as_string(False)
    )

    return config


def columns_of(db_path: Path, table: str) -> list[str]:
    engine = create_engine(sqlite_url(db_path))
    try:
        return [column["name"] for column in inspect(engine).get_columns(table)]
    finally:
        engine.dispose()


def tables_of(db_path: Path) -> set[str]:
    engine = create_engine(sqlite_url(db_path))
    try:
        return set(inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()


def test_upgrade_head_creates_both_tables_with_the_new_column(
    alembic_config: Config, db_path: Path
) -> None:
    command.upgrade(alembic_config, "head")

    assert tables_of(db_path) == {"devices", "manufacturers"}
    assert "location" in columns_of(db_path, "devices")
    assert columns_of(db_path, "manufacturers") == ["id", "name"]

    with sqlite3.connect(db_path) as connection:
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()

    assert version == ("0002",)


def test_models_and_migrations_are_in_sync(
    alembic_config: Config, db_path: Path
) -> None:
    """`alembic check` fails if a model change has no migration."""
    command.upgrade(alembic_config, "head")

    command.check(alembic_config)


def test_downgrade_removes_the_column_and_keeps_the_data(
    alembic_config: Config, db_path: Path
) -> None:
    command.upgrade(alembic_config, "head")
    with sqlite3.connect(db_path) as connection:
        connection.execute("INSERT INTO manufacturers (name) VALUES ('Dell')")
        connection.execute(
            "INSERT INTO devices (inventory_number, device_type, model, cost, "
            "manufacturer_id, location) VALUES ('PC-1', 'Laptop', 'XPS', 10, 1, 'R1')"
        )

    command.downgrade(alembic_config, "0001")

    assert "location" not in columns_of(db_path, "devices")
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute("SELECT inventory_number, model FROM devices").fetchall()

    assert rows == [("PC-1", "XPS")]


def test_upgrade_keeps_old_rows_and_fills_location_with_null(
    alembic_config: Config, db_path: Path
) -> None:
    command.upgrade(alembic_config, "0001")
    with sqlite3.connect(db_path) as connection:
        connection.execute("INSERT INTO manufacturers (name) VALUES ('HP')")
        connection.execute(
            "INSERT INTO devices (inventory_number, device_type, model, cost, "
            "manufacturer_id) VALUES ('PC-2', 'Printer', 'LaserJet', 5, 1)"
        )

    command.upgrade(alembic_config, "head")

    with sqlite3.connect(db_path) as connection:
        row = connection.execute("SELECT model, location FROM devices").fetchone()

    assert row == ("LaserJet", None)


def test_full_downgrade_drops_everything_and_upgrade_is_repeatable(
    alembic_config: Config, db_path: Path
) -> None:
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "base")

    assert tables_of(db_path) == set()

    command.upgrade(alembic_config, "head")

    assert "location" in columns_of(db_path, "devices")
