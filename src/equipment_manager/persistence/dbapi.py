"""Plain Python DB-API (sqlite3) without ORM: parameterized SQL.

Values are never formatted into the SQL text. They are passed separately
as parameters, so input such as "x' OR '1'='1" is treated as plain data.
"""

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import NamedTuple

SEARCH_SQL = """
    SELECT
        devices.inventory_number,
        devices.device_type,
        manufacturers.name,
        devices.model,
        devices.cost
    FROM devices
    JOIN manufacturers
        ON devices.manufacturer_id = manufacturers.id
    WHERE (? IS NULL OR devices.inventory_number = ?)
      AND (? IS NULL OR manufacturers.name = ?)
    ORDER BY devices.inventory_number
"""

UPDATE_COST_SQL = """
    UPDATE devices
    SET cost = ?
    WHERE inventory_number = ?
"""


class DeviceRow(NamedTuple):
    inventory_number: str
    device_type: str
    manufacturer: str
    model: str
    cost: float


def search_devices(
    database_path: str | Path,
    *,
    inventory_number: str | None = None,
    manufacturer: str | None = None,
) -> list[DeviceRow]:
    """Search by inventory number and/or manufacturer (exact, ignoring case)."""
    parameters = (
        inventory_number,
        inventory_number,
        manufacturer,
        manufacturer,
    )

    with closing(sqlite3.connect(database_path)) as connection:
        cursor = connection.cursor()
        cursor.execute(SEARCH_SQL, parameters)

        return [DeviceRow(*row) for row in cursor.fetchall()]


def update_cost(
    database_path: str | Path,
    inventory_number: str,
    cost: float,
) -> bool:
    """UPDATE through DB-API with an explicit commit() / rollback().

    Returns False when no device has this inventory number. A negative
    cost violates the CHECK constraint and the transaction is rolled back.
    """
    connection = sqlite3.connect(database_path)

    try:
        cursor = connection.execute(UPDATE_COST_SQL, (cost, inventory_number))
        connection.commit()

        return cursor.rowcount > 0
    except sqlite3.Error:
        connection.rollback()
        raise
    finally:
        connection.close()
