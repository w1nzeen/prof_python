"""Service layer: business rules and transaction boundaries.

Every public method that changes data runs inside `transaction()`:
COMMIT when the whole operation succeeds, ROLLBACK on any error.
"""

import math
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy.orm import Session

from equipment_manager.exceptions import DuplicateDeviceError, InvalidDeviceError
from equipment_manager.models import Device
from equipment_manager.persistence.exceptions import RecordNotFoundError
from equipment_manager.persistence.models import DeviceModel
from equipment_manager.persistence.repositories import (
    DeviceRepository,
    ManufacturerRepository,
)


@dataclass(frozen=True)
class Statistics:
    """Aggregates of laboratory work 1, now calculated by SQL."""

    count: int
    total_cost: float
    average_cost: float
    most_expensive: DeviceModel | None
    count_by_manufacturer: dict[str, int]


class EquipmentService:
    """Use cases of the equipment manager on top of the repositories."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.manufacturers = ManufacturerRepository(session)
        self.devices = DeviceRepository(session)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Atomic unit of work: commit on success, rollback on any error."""
        try:
            yield
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    # ----- Create ---------------------------------------------------------

    def register_device(
        self,
        device: Device,
        location: str | None = None,
    ) -> DeviceModel:
        with self.transaction():
            return self._register(device, location)

    def register_devices_batch(
        self,
        devices: Sequence[Device],
    ) -> list[DeviceModel]:
        """Register many devices as ONE transaction (all or nothing).

        If any device fails (for example a duplicate inventory number),
        nothing is stored, including manufacturers created by this call.
        """
        with self.transaction():
            return [self._register(device, None) for device in devices]

    def _register(self, device: Device, location: str | None) -> DeviceModel:
        number = device.inventory_number.strip()

        if self.devices.get_by_inventory_number(number) is not None:
            raise DuplicateDeviceError(f"Device {number} already exists.")

        manufacturer = self.manufacturers.get_by_name(device.manufacturer)

        if manufacturer is None:
            manufacturer = self.manufacturers.add(device.manufacturer)

        return self.devices.add(
            DeviceModel(
                inventory_number=number,
                device_type=device.device_type.strip(),
                model=device.model.strip(),
                cost=device.cost,
                manufacturer=manufacturer,
                location=location,
            )
        )

    # ----- Read -----------------------------------------------------------

    def get_device(self, inventory_number: str) -> DeviceModel:
        device = self.devices.get_by_inventory_number(inventory_number)

        if device is None:
            raise RecordNotFoundError(f"Device {inventory_number} not found.")

        return device

    def list_devices(self) -> list[DeviceModel]:
        return self.devices.get_all()

    def search_devices(self, query: str) -> list[DeviceModel]:
        return self.devices.search(query)

    def filter_by_manufacturer(self, manufacturer: str) -> list[DeviceModel]:
        return self.devices.find_by_manufacturer(manufacturer)

    def statistics(self) -> Statistics:
        return Statistics(
            count=self.devices.count(),
            total_cost=self.devices.total_cost(),
            average_cost=self.devices.average_cost(),
            most_expensive=self.devices.most_expensive(),
            count_by_manufacturer=self.devices.count_by_manufacturer(),
        )

    # ----- Update ---------------------------------------------------------

    def change_cost(self, inventory_number: str, cost: float) -> DeviceModel:
        if not math.isfinite(cost) or cost < 0:
            raise InvalidDeviceError("Cost must be a non-negative number.")

        with self.transaction():
            device = self.get_device(inventory_number)
            device.cost = cost

            return self.devices.update(device)

    def change_location(
        self,
        inventory_number: str,
        location: str | None,
    ) -> DeviceModel:
        with self.transaction():
            device = self.get_device(inventory_number)
            device.location = location.strip() if location else None

            return self.devices.update(device)

    # ----- Delete ---------------------------------------------------------

    def remove_device(self, inventory_number: str) -> None:
        with self.transaction():
            device = self.get_device(inventory_number)
            self.devices.delete(device.id)
