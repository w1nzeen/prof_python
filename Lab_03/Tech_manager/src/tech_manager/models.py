from dataclasses import dataclass


@dataclass(frozen=True)
class Tech:
    """Пристрій комп'ютерної техніки (модель з Lab 01).

    frozen=True робить об'єкт незмінним і hashable.
    """

    inventory_number: str
    type: str
    vendor: str
    model: str
    price: float

    @property
    def name(self) -> str:
        return f"{self.type}: {self.vendor} {self.model}"

    @property
    def vendor_model(self) -> tuple[str, str]:
        """Пара (виробник, модель) - логічно єдина, незмінна група даних."""
        return (self.vendor, self.model)
