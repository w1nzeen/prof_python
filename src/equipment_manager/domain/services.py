"""Application layer: use cases built from injected dependencies."""

import logging
from datetime import date

from equipment_manager.domain.dto import InventoryReport
from equipment_manager.domain.models import (
    Device,
    DeviceStatus,
    InventoryRegistry,
    MaintenanceRecord,
)
from equipment_manager.domain.policies import MaintenancePolicy
from equipment_manager.domain.protocols import Notifier, ReportFormatter
from equipment_manager.domain.value_objects import NumberLike

logger = logging.getLogger(__name__)


class MaintenanceService:
    """Finds devices that need maintenance and records the work done."""

    def __init__(
        self,
        registry: InventoryRegistry,
        policy: MaintenancePolicy,
        notifier: Notifier,
        recipient: str = "it-support@example.com",
    ) -> None:
        self._registry = registry
        self._policy = policy
        self._notifier = notifier
        self._recipient = recipient

    def due_devices(self, today: date) -> list[Device]:
        return [
            d
            for d in self._registry
            if d.status is not DeviceStatus.DECOMMISSIONED
            and self._policy.is_due(d, today)
        ]

    def notify_due(self, today: date) -> int:
        devices = self.due_devices(today)

        for device in devices:
            due_date = self._policy.next_due(device)
            self._notifier.send(
                self._recipient,
                f"Maintenance due since {due_date}: {device}",
            )

        return len(devices)

    def perform(
        self,
        number: NumberLike,
        description: str,
        performed_on: date,
        technician: str = "",
    ) -> MaintenanceRecord:
        device = self._registry[number]
        record = MaintenanceRecord(performed_on, description, technician)
        device.record_maintenance(record)

        try:
            self._notifier.send(
                self._recipient,
                f"Maintenance done for {device.inventory_number}: {description}",
            )
        except Exception as error:  # noqa: BLE001 - the work is done, keep it
            logger.warning("Notification failed: %s", error)

        return record


class ReportService:
    """Builds and renders inventory reports."""

    def __init__(
        self,
        registry: InventoryRegistry,
        formatter: ReportFormatter,
    ) -> None:
        self._registry = registry
        self._formatter = formatter

    def build_report(self) -> InventoryReport:
        expensive = self._registry.most_expensive()

        return InventoryReport(
            total_devices=len(self._registry),
            total_cost=self._registry.total_cost(),
            average_cost=self._registry.average_cost(),
            most_expensive=str(expensive) if expensive else None,
            by_manufacturer=self._registry.count_by_manufacturer(),
            by_kind=self._registry.count_by_kind(),
        )

    def render(self) -> str:
        return self._formatter.format(self.build_report())
