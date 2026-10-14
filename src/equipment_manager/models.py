"""Data models of the equipment manager."""

from dataclasses import dataclass

from equipment_manager.exceptions import InvalidDeviceError


@dataclass(frozen=True)
class Device:
    """A single piece of computer equipment."""

    inventory_number: str
    device_type: str
    manufacturer: str
    model: str
    cost: float

    def __post_init__(self) -> None:
        text_fields = {
            "inventory_number": self.inventory_number,
            "device_type": self.device_type,
            "manufacturer": self.manufacturer,
            "model": self.model,
        }

        for name, value in text_fields.items():
            if not value.strip():
                raise InvalidDeviceError(f"Field '{name}' must not be empty.")

        if self.cost < 0:
            raise InvalidDeviceError("Cost must not be negative.")

    @property
    def full_name(self) -> str:
        return f"{self.manufacturer} {self.model}"
