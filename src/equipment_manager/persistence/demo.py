"""Console demonstration of laboratory work 7 (database persistence)."""

from collections.abc import Sequence
from pathlib import Path

from equipment_manager.data import DEVICES
from equipment_manager.exceptions import EquipmentError
from equipment_manager.models import Device
from equipment_manager.persistence import dbapi
from equipment_manager.persistence.database import (
    create_db_engine,
    create_session_factory,
    init_db,
    sqlite_url,
)
from equipment_manager.persistence.models import DeviceModel
from equipment_manager.persistence.services import EquipmentService


def print_rows(devices: Sequence[DeviceModel]) -> None:
    if not devices:
        print("  (nothing found)")
        return

    for device in devices:
        print(
            f"  {device.id:>3} {device.inventory_number:<8}"
            f"{device.device_type:<10}{device.manufacturer.name:<9}"
            f"{device.model:<20}{device.cost:>10.2f}"
            f"  {device.location or '-'}"
        )


def run_database_demo(database_path: Path) -> None:
    """Create a fresh database file and walk through the whole lab."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_path.unlink(missing_ok=True)

    engine = create_db_engine(sqlite_url(database_path))
    init_db(engine)
    session_factory = create_session_factory(engine)
    print(f"Database: {database_path}")

    with session_factory() as session:
        service = EquipmentService(session)

        service.register_devices_batch(DEVICES)
        print(f"\nRegistered {len(DEVICES)} devices in one transaction.")

        print("\nAll devices (SELECT ... JOIN):")
        print_rows(service.list_devices())

        print("\nSearch 'laptop':")
        print_rows(service.search_devices("laptop"))

        print("\nManufacturer = Lenovo:")
        print_rows(service.filter_by_manufacturer("Lenovo"))

        stats = service.statistics()
        print("\nStatistics (SUM, AVG, ORDER BY ... LIMIT 1):")
        print(f"  Devices count: {stats.count}")
        print(f"  Total cost: {stats.total_cost:.2f}")
        print(f"  Average cost: {stats.average_cost:.2f}")

        if stats.most_expensive is not None:
            print(f"  Most expensive: {stats.most_expensive.full_name}")

        print(f"  Devices per manufacturer (GROUP BY): {stats.count_by_manufacturer}")

        print("\nDB-API (sqlite3, parameterized query), manufacturer = HP:")
        for row in dbapi.search_devices(database_path, manufacturer="HP"):
            print(f"  {row.inventory_number} {row.model} {row.cost:.2f}")

        service.change_cost("PC-012", 500.0)
        service.change_location("PC-012", "Room 101")
        service.remove_device("PC-011")
        print("\nUpdated PC-012 (cost, location) and deleted PC-011:")
        print_rows(service.search_devices("PC-01"))

        count_before = service.devices.count()
        bad_batch = [
            Device("PC-100", "Laptop", "Acer", "Swift 3", 25000.0),
            Device("PC-001", "Laptop", "Acer", "Swift 5", 31000.0),
        ]

        print("\nTransaction: batch with a duplicate inventory number (PC-001)")
        try:
            service.register_devices_batch(bad_batch)
        except EquipmentError as error:
            print(f"  Error: {error} -> ROLLBACK")

        rolled_back = service.devices.get_by_inventory_number("PC-100") is None
        print(f"  Devices before/after: {count_before}/{service.devices.count()}")
        print(f"  PC-100 was not stored: {rolled_back}")
        print(f"  Manufacturer Acer was not stored: "
              f"{service.manufacturers.get_by_name('Acer') is None}")

    engine.dispose()
