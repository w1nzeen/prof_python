"""Domain entities: Manufacturer, Device, Computer, Printer, registry."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import ClassVar, TypeVar

from equipment_manager.domain.exceptions import (
    DeviceNotFoundError,
    InvalidValueError,
    MaintenanceError,
)
from equipment_manager.domain.protocols import Repository
from equipment_manager.domain.value_objects import (
    InventoryNumber,
    Money,
    NumberLike,
)


@dataclass(frozen=True, slots=True)
class Manufacturer:
    """Manufacturer of equipment (immutable)."""

    name: str
    country: str = ""

    def __post_init__(self) -> None:
        name = self.name.strip()

        if not name:
            raise InvalidValueError("Manufacturer name must not be empty")

        object.__setattr__(self, "name", name)

    def matches(self, name: str) -> bool:
        return self.name.casefold() == name.strip().casefold()

    def __str__(self) -> str:
        return self.name


class PrintTechnology(str, Enum):
    LASER = "laser"
    INKJET = "inkjet"


@dataclass(frozen=True, slots=True)
class MaintenanceRecord:
    performed_on: date
    description: str
    technician: str = ""

    def __post_init__(self) -> None:
        if not self.description.strip():
            raise InvalidValueError("Description must not be empty")


class Device:
    """Base class of all equipment.

    State is private; it is changed only through validated methods.
    `kind` is a class-level attribute overridden in subclasses.
    """

    kind: ClassVar[str] = "Device"

    def __init__(
        self,
        *,
        inventory_number: InventoryNumber,
        manufacturer: Manufacturer,
        model: str,
        cost: Money,
        purchased_on: date,
    ) -> None:
        if not model.strip():
            raise InvalidValueError("Model must not be empty")

        self._inventory_number = inventory_number
        self._manufacturer = manufacturer
        self.model = model.strip()
        self._cost = cost
        self._purchased_on = purchased_on
        self._maintenance_log: list[MaintenanceRecord] = []

    @property
    def inventory_number(self) -> InventoryNumber:
        return self._inventory_number

    @property
    def manufacturer(self) -> Manufacturer:
        return self._manufacturer

    @property
    def purchased_on(self) -> date:
        return self._purchased_on

    @property
    def cost(self) -> Money:
        return self._cost

    @cost.setter
    def cost(self, value: Money) -> None:
        if value.currency != self._cost.currency:
            raise InvalidValueError("Currency of a device cannot change")

        self._cost = value

    @property
    def full_name(self) -> str:
        return f"{self._manufacturer.name} {self.model}"

    @property
    def maintenance_history(self) -> tuple[MaintenanceRecord, ...]:
        return tuple(self._maintenance_log)

    @property
    def last_service_date(self) -> date:
        if self._maintenance_log:
            return self._maintenance_log[-1].performed_on

        return self._purchased_on

    def record_maintenance(self, record: MaintenanceRecord) -> None:
        if record.performed_on < self.last_service_date:
            raise MaintenanceError(
                "Maintenance cannot be earlier than the previous service"
            )

        self._maintenance_log.append(record)

    def specifications(self) -> dict[str, str]:
        return {}

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"inventory_number={str(self._inventory_number)!r}, "
            f"model={self.model!r}, cost={str(self._cost)!r})"
        )

    def __str__(self) -> str:
        return (
            f"{self._inventory_number} {self.kind}: "
            f"{self.full_name} ({self._cost})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Device):
            return NotImplemented

        return self._inventory_number == other._inventory_number

    def __hash__(self) -> int:
        return hash(self._inventory_number)


class Computer(Device):
    kind: ClassVar[str] = "Computer"

    def __init__(
        self,
        *,
        inventory_number: InventoryNumber,
        manufacturer: Manufacturer,
        model: str,
        cost: Money,
        purchased_on: date,
        cpu: str,
        ram_gb: int,
        storage_gb: int,
    ) -> None:
        super().__init__(
            inventory_number=inventory_number,
            manufacturer=manufacturer,
            model=model,
            cost=cost,
            purchased_on=purchased_on,
        )

        if ram_gb <= 0 or storage_gb <= 0:
            raise InvalidValueError("RAM and storage must be positive")

        self.cpu = cpu
        self.ram_gb = ram_gb
        self.storage_gb = storage_gb

    def specifications(self) -> dict[str, str]:
        return {
            **super().specifications(),
            "CPU": self.cpu,
            "RAM": f"{self.ram_gb} GB",
            "Storage": f"{self.storage_gb} GB",
        }


class Printer(Device):
    kind: ClassVar[str] = "Printer"

    def __init__(
        self,
        *,
        inventory_number: InventoryNumber,
        manufacturer: Manufacturer,
        model: str,
        cost: Money,
        purchased_on: date,
        technology: PrintTechnology,
        pages_per_minute: int,
    ) -> None:
        super().__init__(
            inventory_number=inventory_number,
            manufacturer=manufacturer,
            model=model,
            cost=cost,
            purchased_on=purchased_on,
        )

        if pages_per_minute <= 0:
            raise InvalidValueError("Pages per minute must be positive")

        self.technology = technology
        self.pages_per_minute = pages_per_minute

    def specifications(self) -> dict[str, str]:
        return {
            **super().specifications(),
            "Technology": self.technology.value,
            "Speed": f"{self.pages_per_minute} ppm",
        }


D = TypeVar("D", bound=Device)


class InventoryRegistry:
    """Custom collection of devices; storage is injected (DIP)."""

    def __init__(
        self,
        repository: Repository[InventoryNumber, Device],
    ) -> None:
        self._repository = repository

    def register(self, device: Device) -> None:
        self._repository.add(device)

    def unregister(self, number: NumberLike) -> bool:
        return self._repository.remove(InventoryNumber.parse(number))

    def find(self, number: NumberLike) -> Device | None:
        return self._repository.get(InventoryNumber.parse(number))

    def __getitem__(self, number: NumberLike) -> Device:
        device = self.find(number)

        if device is None:
            raise DeviceNotFoundError(f"Device {number} not found")

        return device

    def __contains__(self, number: object) -> bool:
        if not isinstance(number, (str, InventoryNumber)):
            return False

        try:
            return self.find(number) is not None
        except InvalidValueError:
            return False

    def __len__(self) -> int:
        return len(self._repository.keys())

    def __iter__(self) -> Iterator[Device]:
        return iter(self._repository.all())

    def by_manufacturer(self, name: str) -> list[Device]:
        return [d for d in self if d.manufacturer.matches(name)]

    def by_type(self, device_type: type[D]) -> list[D]:
        """Bound TypeVar keeps the precise type: list[Computer]."""
        return [d for d in self if isinstance(d, device_type)]

    def total_cost(self, currency: str = "UAH") -> Money:
        return sum((d.cost for d in self), start=Money.zero(currency))

    def average_cost(self, currency: str = "UAH") -> Money:
        count = len(self)

        if count == 0:
            return Money.zero(currency)

        return self.total_cost(currency) / count

    def most_expensive(self) -> Device | None:
        return max(self, key=lambda device: device.cost, default=None)

    def count_by_manufacturer(self) -> dict[str, int]:
        counts: dict[str, int] = {}

        for device in self:
            name = device.manufacturer.name
            counts[name] = counts.get(name, 0) + 1

        return counts

    def count_by_kind(self) -> dict[str, int]:
        counts: dict[str, int] = {}

        for device in self:
            counts[device.kind] = counts.get(device.kind, 0) + 1

        return counts
