"""Custom exceptions of the equipment manager."""


class EquipmentError(Exception):
    """Base class for all application errors."""


class InvalidDeviceError(EquipmentError):
    """Raised when device data is not valid."""


class DuplicateDeviceError(EquipmentError):
    """Raised when a device with the same inventory number exists."""
