"""Type-checking experiment: the same code after the corrections."""

from datetime import date

from equipment_manager.domain.models import Device, Manufacturer
from equipment_manager.domain.repositories import InMemoryRepository
from equipment_manager.domain.value_objects import InventoryNumber, Money

customer_id: int = 1


def total() -> int:
    return 100


repository: InMemoryRepository[InventoryNumber, Device] = InMemoryRepository(
    lambda device: device.inventory_number
)
repository.add(
    Device(
        inventory_number=InventoryNumber("PC-100"),
        manufacturer=Manufacturer("Dell"),
        model="U2723QE",
        cost=Money.of(17200.5),
        purchased_on=date(2026, 6, 30),
    )
)
