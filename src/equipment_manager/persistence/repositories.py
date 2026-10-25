"""Repository Pattern: all SQL/ORM access lives in these classes.

Repositories never call commit(): they only flush, so that constraint
errors appear immediately. The service layer decides when a transaction
is committed or rolled back (see services.py).
"""

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from equipment_manager.exceptions import (
    DuplicateDeviceError,
    EquipmentError,
    InvalidDeviceError,
)
from equipment_manager.persistence.exceptions import (
    DuplicateManufacturerError,
    ManufacturerInUseError,
    PersistenceError,
    RecordNotFoundError,
    ReferenceIntegrityError,
)
from equipment_manager.persistence.models import DeviceModel, ManufacturerModel


def translate_integrity_error(error: IntegrityError) -> EquipmentError:
    """Turn a low-level constraint error into an application exception."""
    message = str(error.orig)

    if "devices.inventory_number" in message:
        return DuplicateDeviceError("Device with this inventory number exists.")

    if "manufacturers.name" in message:
        return DuplicateManufacturerError("Manufacturer already exists.")

    if "CHECK" in message:
        return InvalidDeviceError("Cost must not be negative.")

    if "FOREIGN KEY" in message:
        return ReferenceIntegrityError("Referenced row is missing or in use.")

    return PersistenceError(message)


def flush(session: Session) -> None:
    """Send pending changes to the database and translate constraint errors."""
    try:
        session.flush()
    except IntegrityError as error:
        raise translate_integrity_error(error) from error


class ManufacturerRepository:
    """CRUD of the `manufacturers` table."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, name: str) -> ManufacturerModel:
        manufacturer = ManufacturerModel(name=name.strip())
        self.session.add(manufacturer)
        flush(self.session)

        return manufacturer

    def get_by_id(self, manufacturer_id: int) -> ManufacturerModel | None:
        return self.session.get(ManufacturerModel, manufacturer_id)

    def get_by_name(self, name: str) -> ManufacturerModel | None:
        statement = select(ManufacturerModel).where(
            ManufacturerModel.name == name.strip()
        )

        return self.session.scalar(statement)

    def get_all(self) -> list[ManufacturerModel]:
        statement = select(ManufacturerModel).order_by(ManufacturerModel.name)

        return list(self.session.scalars(statement))

    def rename(self, manufacturer_id: int, new_name: str) -> ManufacturerModel:
        manufacturer = self.get_by_id(manufacturer_id)

        if manufacturer is None:
            raise RecordNotFoundError(f"Manufacturer {manufacturer_id} not found.")

        manufacturer.name = new_name.strip()
        flush(self.session)

        return manufacturer

    def delete(self, manufacturer_id: int) -> bool:
        """Delete a manufacturer; refuse while it still owns devices."""
        manufacturer = self.get_by_id(manufacturer_id)

        if manufacturer is None:
            return False

        owned = self.session.scalar(
            select(func.count())
            .select_from(DeviceModel)
            .where(DeviceModel.manufacturer_id == manufacturer_id)
        )

        if owned:
            raise ManufacturerInUseError(
                f"Manufacturer {manufacturer.name} still has {owned} device(s)."
            )

        self.session.delete(manufacturer)
        flush(self.session)

        return True


class DeviceRepository:
    """CRUD, search and SQL aggregates of the `devices` table."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ----- Create / Read / Update / Delete -------------------------------

    def add(self, device: DeviceModel) -> DeviceModel:
        self.session.add(device)
        flush(self.session)

        return device

    def get_by_id(self, device_id: int) -> DeviceModel | None:
        return self.session.get(DeviceModel, device_id)

    def get_by_inventory_number(
        self,
        inventory_number: str,
    ) -> DeviceModel | None:
        statement = select(DeviceModel).where(
            DeviceModel.inventory_number == inventory_number.strip()
        )

        return self.session.scalar(statement)

    def get_all(self) -> list[DeviceModel]:
        statement = select(DeviceModel).order_by(DeviceModel.inventory_number)

        return list(self.session.scalars(statement))

    def update(self, device: DeviceModel) -> DeviceModel:
        """Persist changes made to a loaded device."""
        flush(self.session)

        return device

    def delete(self, device_id: int) -> bool:
        device = self.get_by_id(device_id)

        if device is None:
            return False

        self.session.delete(device)
        flush(self.session)

        return True

    # ----- Search and filters -------------------------------------------

    def find_by_manufacturer(self, name: str) -> list[DeviceModel]:
        statement = (
            select(DeviceModel)
            .join(ManufacturerModel)
            .where(ManufacturerModel.name == name.strip())
            .order_by(DeviceModel.inventory_number)
        )

        return list(self.session.scalars(statement))

    def search(self, query: str) -> list[DeviceModel]:
        """Part of inventory number, type, model or manufacturer name."""
        text = query.strip()
        statement = (
            select(DeviceModel)
            .join(ManufacturerModel)
            .where(
                or_(
                    DeviceModel.inventory_number.contains(text, autoescape=True),
                    DeviceModel.device_type.contains(text, autoescape=True),
                    DeviceModel.model.contains(text, autoescape=True),
                    ManufacturerModel.name.contains(text, autoescape=True),
                )
            )
            .order_by(DeviceModel.inventory_number)
        )

        return list(self.session.scalars(statement))

    # ----- Aggregates computed by the database --------------------------

    def count(self) -> int:
        return int(self.session.scalar(select(func.count(DeviceModel.id))) or 0)

    def total_cost(self) -> float:
        result = self.session.scalar(select(func.sum(DeviceModel.cost)))

        return float(result) if result is not None else 0.0

    def average_cost(self) -> float:
        result = self.session.scalar(select(func.avg(DeviceModel.cost)))

        return float(result) if result is not None else 0.0

    def most_expensive(self) -> DeviceModel | None:
        statement = (
            select(DeviceModel)
            .order_by(DeviceModel.cost.desc(), DeviceModel.id)
            .limit(1)
        )

        return self.session.scalar(statement)

    def count_by_manufacturer(self) -> dict[str, int]:
        """JOIN + GROUP BY: number of devices per manufacturer."""
        statement = (
            select(ManufacturerModel.name, func.count(DeviceModel.id))
            .join(DeviceModel)
            .group_by(ManufacturerModel.name)
            .order_by(ManufacturerModel.name)
        )

        return {name: count for name, count in self.session.execute(statement)}

    def total_cost_by_manufacturer(self) -> dict[str, float]:
        """JOIN + GROUP BY: total cost per manufacturer."""
        statement = (
            select(ManufacturerModel.name, func.sum(DeviceModel.cost))
            .join(DeviceModel)
            .group_by(ManufacturerModel.name)
            .order_by(ManufacturerModel.name)
        )

        return {
            name: float(total) for name, total in self.session.execute(statement)
        }
