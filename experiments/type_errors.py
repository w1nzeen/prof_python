"""Type-checking experiment: three intentional errors (do not run)."""

from equipment_manager.domain.models import Device, Manufacturer
from equipment_manager.domain.repositories import InMemoryRepository
from equipment_manager.domain.value_objects import InventoryNumber

# Error 1: str assigned to int
customer_id: int = "1"


# Error 2: function declared to return int returns str
def total() -> int:
    return "100"


# Error 3: a Manufacturer is added to a repository of devices
repository: InMemoryRepository[InventoryNumber, Device] = InMemoryRepository(
    lambda device: device.inventory_number
)
repository.add(Manufacturer("Dell"))
