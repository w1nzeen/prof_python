from dataclasses import dataclass

@dataclass
class Tech:
    inventory_number: str
    type: str
    vendor: str
    model: str
    price: float

    @property
    def name(self) -> str:
        return f"{self.type}: {self.vendor} {self.model}"