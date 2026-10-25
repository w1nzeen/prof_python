"""Exceptions of the persistence layer."""

from equipment_manager.exceptions import EquipmentError


class PersistenceError(EquipmentError):
    """Base class for all database-related errors."""


class RecordNotFoundError(PersistenceError, LookupError):
    """The requested row does not exist."""


class DuplicateManufacturerError(PersistenceError):
    """A manufacturer with the same name already exists."""


class ReferenceIntegrityError(PersistenceError):
    """A FOREIGN KEY constraint would be violated."""


class ManufacturerInUseError(ReferenceIntegrityError):
    """The manufacturer still owns devices and cannot be deleted."""
