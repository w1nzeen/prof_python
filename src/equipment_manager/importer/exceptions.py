"""Exception hierarchy of the importer."""

from equipment_manager.exceptions import EquipmentError


class ApplicationError(EquipmentError):
    """Base application exception."""


class ConfigurationError(ApplicationError):
    """Configuration is invalid."""


class DataError(ApplicationError):
    """Base data exception."""


class DataValidationError(DataError):
    """External data violates a validation rule."""


class DataImportError(DataError):
    """Input data cannot be imported."""


class DataExportError(DataError):
    """Output cannot be written."""


class RecordValidationError(DataValidationError):
    """A single record is invalid; carries the place of the problem."""

    def __init__(
        self,
        message: str,
        *,
        line_number: int | None = None,
        field: str | None = None,
        value: str | None = None,
    ) -> None:
        super().__init__(message)
        self.line_number = line_number
        self.field = field
        self.value = value
