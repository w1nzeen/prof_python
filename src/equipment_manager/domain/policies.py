"""Maintenance policies: strategy pattern on top of an ABC."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import date, timedelta

from equipment_manager.domain.exceptions import InvalidValueError
from equipment_manager.domain.models import Device


class MaintenancePolicy(ABC):
    """Decides how often a device needs maintenance."""

    @abstractmethod
    def interval_for(self, device: Device) -> int:
        """Return the maintenance interval in days (always positive)."""

    def next_due(self, device: Device) -> date:
        return device.last_service_date + timedelta(
            days=self.interval_for(device)
        )

    def is_due(self, device: Device, today: date) -> bool:
        return self.next_due(device) <= today


class FixedIntervalPolicy(MaintenancePolicy):
    def __init__(self, days: int) -> None:
        if days <= 0:
            raise InvalidValueError("Interval must be positive")

        self.days = days

    def interval_for(self, device: Device) -> int:
        return self.days


class ByKindPolicy(MaintenancePolicy):
    """Composition: chooses a policy by device class (or its base class)."""

    def __init__(
        self,
        policies: Mapping[type[Device], MaintenancePolicy],
        default: MaintenancePolicy,
    ) -> None:
        self._policies = dict(policies)
        self._default = default

    def interval_for(self, device: Device) -> int:
        for cls in type(device).__mro__:
            policy = self._policies.get(cls)

            if policy is not None:
                return policy.interval_for(device)

        return self._default.interval_for(device)
