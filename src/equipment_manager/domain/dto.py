"""Data transfer objects: TypedDict payloads and the report DTO."""

from dataclasses import dataclass, field
from datetime import date
from typing import Literal, NotRequired, TypeAlias, TypedDict

from equipment_manager.domain.exceptions import InvalidValueError
from equipment_manager.domain.models import (
    Computer,
    Device,
    Manufacturer,
    Printer,
    PrintTechnology,
)
from equipment_manager.domain.value_objects import InventoryNumber, Money


class BasePayload(TypedDict):
    """Plain dictionary received from an external system (JSON-like)."""

    inventory_number: str
    manufacturer: str
    model: str
    cost: float
    purchased_on: str
    currency: NotRequired[str]
    country: NotRequired[str]


class GenericPayload(BasePayload):
    kind: Literal["device"]


class ComputerPayload(BasePayload):
    kind: Literal["computer"]
    cpu: str
    ram_gb: int
    storage_gb: int


class PrinterPayload(BasePayload):
    kind: Literal["printer"]
    technology: str
    pages_per_minute: int


DevicePayload: TypeAlias = GenericPayload | ComputerPayload | PrinterPayload


def device_from_payload(payload: DevicePayload) -> Device:
    """Convert an external payload to a domain object."""
    try:
        number = InventoryNumber(payload["inventory_number"])
        manufacturer = Manufacturer(
            payload["manufacturer"],
            payload.get("country", ""),
        )
        cost = Money.of(payload["cost"], payload.get("currency", "UAH"))
        purchased_on = date.fromisoformat(payload["purchased_on"])

        if payload["kind"] == "computer":
            return Computer(
                inventory_number=number,
                manufacturer=manufacturer,
                model=payload["model"],
                cost=cost,
                purchased_on=purchased_on,
                cpu=payload["cpu"],
                ram_gb=payload["ram_gb"],
                storage_gb=payload["storage_gb"],
            )

        if payload["kind"] == "printer":
            return Printer(
                inventory_number=number,
                manufacturer=manufacturer,
                model=payload["model"],
                cost=cost,
                purchased_on=purchased_on,
                technology=PrintTechnology(payload["technology"]),
                pages_per_minute=payload["pages_per_minute"],
            )

        return Device(
            inventory_number=number,
            manufacturer=manufacturer,
            model=payload["model"],
            cost=cost,
            purchased_on=purchased_on,
        )
    except InvalidValueError:
        raise
    except (KeyError, ValueError, ArithmeticError) as error:
        raise InvalidValueError(f"Invalid payload: {error!r}") from error


def device_to_payload(device: Device) -> DevicePayload:
    """Convert a domain object back to a plain dictionary."""
    number = str(device.inventory_number)
    name = device.manufacturer.name
    country = device.manufacturer.country
    cost = float(device.cost.amount)
    currency = device.cost.currency
    purchased_on = device.purchased_on.isoformat()

    if isinstance(device, Computer):
        return {
            "kind": "computer",
            "inventory_number": number,
            "manufacturer": name,
            "country": country,
            "model": device.model,
            "cost": cost,
            "currency": currency,
            "purchased_on": purchased_on,
            "cpu": device.cpu,
            "ram_gb": device.ram_gb,
            "storage_gb": device.storage_gb,
        }

    if isinstance(device, Printer):
        return {
            "kind": "printer",
            "inventory_number": number,
            "manufacturer": name,
            "country": country,
            "model": device.model,
            "cost": cost,
            "currency": currency,
            "purchased_on": purchased_on,
            "technology": device.technology.value,
            "pages_per_minute": device.pages_per_minute,
        }

    return {
        "kind": "device",
        "inventory_number": number,
        "manufacturer": name,
        "country": country,
        "model": device.model,
        "cost": cost,
        "currency": currency,
        "purchased_on": purchased_on,
    }


@dataclass(frozen=True)
class InventoryReport:
    """Result of ReportService; a DTO without behaviour."""

    total_devices: int
    total_cost: Money
    average_cost: Money
    most_expensive: str | None
    by_manufacturer: dict[str, int] = field(default_factory=dict)
    by_kind: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "total_devices": self.total_devices,
            "total_cost": self.total_cost.to_dict(),
            "average_cost": self.average_cost.to_dict(),
            "most_expensive": self.most_expensive,
            "by_manufacturer": dict(self.by_manufacturer),
            "by_kind": dict(self.by_kind),
        }
