"""Exception hierarchy of the domain layer."""

from equipment_manager.exceptions import EquipmentError


class DomainError(EquipmentError):
    """Base class for all domain errors."""


class InvalidValueError(DomainError, ValueError):
    """A value object or entity received invalid data."""


class CurrencyMismatchError(InvalidValueError):
    """Money in different currencies was combined or compared."""


class DuplicateKeyError(DomainError):
    """An item with the same key is already stored."""


class DeviceNotFoundError(DomainError, LookupError):
    """No device with the requested inventory number."""


class MaintenanceError(DomainError):
    """A maintenance operation is not allowed."""


class InvalidStatusTransitionError(DomainError):
    """The requested device status change is not allowed."""


class InventorySyncError(DomainError):
    """The external inventory provider failed."""
