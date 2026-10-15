"""Manual dependency injection container (composition root)."""

from dataclasses import dataclass

from equipment_manager.domain.adapters import (
    ConsoleNotifier,
    TextReportFormatter,
)
from equipment_manager.domain.models import (
    Computer,
    Device,
    InventoryRegistry,
    Printer,
)
from equipment_manager.domain.policies import (
    ByKindPolicy,
    FixedIntervalPolicy,
    MaintenancePolicy,
)
from equipment_manager.domain.protocols import (
    Notifier,
    ReportFormatter,
    Repository,
)
from equipment_manager.domain.repositories import InMemoryRepository
from equipment_manager.domain.services import (
    MaintenanceService,
    ReportService,
)
from equipment_manager.domain.value_objects import InventoryNumber


@dataclass(frozen=True)
class Container:
    repository: Repository[InventoryNumber, Device]
    registry: InventoryRegistry
    notifier: Notifier
    maintenance: MaintenanceService
    reports: ReportService


def default_policy() -> MaintenancePolicy:
    return ByKindPolicy(
        {
            Computer: FixedIntervalPolicy(180),
            Printer: FixedIntervalPolicy(90),
        },
        default=FixedIntervalPolicy(365),
    )


def build_container(
    *,
    notifier: Notifier | None = None,
    formatter: ReportFormatter | None = None,
    policy: MaintenancePolicy | None = None,
) -> Container:
    """Create all objects once; every dependency can be replaced."""
    repository: Repository[InventoryNumber, Device] = InMemoryRepository(
        lambda device: device.inventory_number
    )
    registry = InventoryRegistry(repository)
    used_notifier = notifier if notifier is not None else ConsoleNotifier()

    return Container(
        repository=repository,
        registry=registry,
        notifier=used_notifier,
        maintenance=MaintenanceService(
            registry,
            policy if policy is not None else default_policy(),
            used_notifier,
        ),
        reports=ReportService(
            registry,
            formatter if formatter is not None else TextReportFormatter(),
        ),
    )
