"""Loading and validation of the YAML configuration."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

import yaml

from equipment_manager.importer.exceptions import ConfigurationError

SUPPORTED_VERSION = 1
INPUT_FORMATS = ("auto", "csv", "json", "jsonl")
OUTPUT_FORMATS = ("auto", "json", "jsonl")
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
DEFAULT_STATUSES = ("in_use", "in_storage", "in_repair", "decommissioned")

T = TypeVar("T")


@dataclass(frozen=True)
class InputConfig:
    path: Path
    format: str = "auto"


@dataclass(frozen=True)
class OutputConfig:
    path: Path
    format: str = "auto"
    backup_existing: bool = False
    summary_path: Path | None = None


@dataclass(frozen=True)
class ProcessingConfig:
    skip_invalid: bool
    minimum_value: float
    allowed_types: tuple[str, ...]
    allowed_manufacturers: tuple[str, ...]
    allowed_statuses: tuple[str, ...] = DEFAULT_STATUSES


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"
    path: Path | None = None
    errors_path: Path | None = None
    max_bytes: int = 1_048_576
    backup_count: int = 3


@dataclass(frozen=True)
class AppConfig:
    version: int
    input: InputConfig
    output: OutputConfig
    processing: ProcessingConfig
    logging: LoggingConfig


def _section(data: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = data.get(key)

    if value is None:
        raise ConfigurationError(f"Missing configuration section: '{key}'")

    if not isinstance(value, Mapping):
        raise ConfigurationError(f"Section '{key}' must be a mapping")

    return {str(k): v for k, v in value.items()}


def _get(
    section: Mapping[str, object],
    key: str,
    expected: type[T],
    where: str,
    default: T | None = None,
) -> T:
    """Read a required (or defaulted) key and check its type."""
    if key not in section or section[key] is None:
        if default is not None:
            return default

        raise ConfigurationError(f"Missing configuration key: '{where}.{key}'")

    value = section[key]

    # bool is a subclass of int, so it must be rejected explicitly
    if not isinstance(value, expected) or (
        expected is not bool and isinstance(value, bool)
    ):
        raise ConfigurationError(
            f"'{where}.{key}' must be of type {expected.__name__}"
        )

    return value


def _optional_path(
    section: Mapping[str, object],
    key: str,
    where: str,
    base: Path,
) -> Path | None:
    if section.get(key) is None:
        return None

    return _resolve(_get(section, key, str, where), base)


def _resolve(value: str, base: Path) -> Path:
    path = Path(value)

    return path if path.is_absolute() else base / path


def _string_list(
    section: Mapping[str, object],
    key: str,
    where: str,
) -> tuple[str, ...]:
    value = section.get(key)

    if value is None:
        raise ConfigurationError(f"Missing configuration key: '{where}.{key}'")

    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        raise ConfigurationError(f"'{where}.{key}' must be a list of strings")

    return tuple(str(item) for item in value)


def _to_bool(text: str, name: str) -> bool:
    lowered = text.strip().lower()

    if lowered in {"1", "true", "yes", "on"}:
        return True

    if lowered in {"0", "false", "no", "off"}:
        return False

    raise ConfigurationError(f"Environment variable {name} must be a boolean")


def _apply_environment(
    data: dict[str, object],
    environ: Mapping[str, str],
) -> None:
    """Environment variables override selected values from the file."""
    mapping: dict[str, tuple[str, str]] = {
        "IMPORTER_INPUT_PATH": ("input", "path"),
        "IMPORTER_OUTPUT_PATH": ("output", "path"),
        "IMPORTER_SKIP_INVALID": ("processing", "skip_invalid"),
        "IMPORTER_MINIMUM_VALUE": ("processing", "minimum_value"),
        "IMPORTER_LOG_LEVEL": ("logging", "level"),
    }

    for name, (section_name, key) in mapping.items():
        if name not in environ:
            continue

        section = data.setdefault(section_name, {})

        if not isinstance(section, dict):
            raise ConfigurationError(f"Section '{section_name}' must be a mapping")

        text = environ[name]

        if key == "skip_invalid":
            section[key] = _to_bool(text, name)
        elif key == "minimum_value":
            try:
                section[key] = float(text)
            except ValueError as error:
                raise ConfigurationError(
                    f"Environment variable {name} must be a number"
                ) from error
        else:
            section[key] = text


def load_config(
    path: Path,
    environ: Mapping[str, str] | None = None,
) -> AppConfig:
    """Read config.yaml; relative paths are relative to the config file."""
    try:
        with path.open("r", encoding="utf-8") as file:
            loaded = yaml.safe_load(file)
    except FileNotFoundError as error:
        raise ConfigurationError(f"Configuration file not found: {path}") from error
    except yaml.YAMLError as error:
        raise ConfigurationError(f"Invalid YAML in {path}") from error
    except (OSError, UnicodeDecodeError) as error:
        raise ConfigurationError(f"Cannot read configuration {path}") from error

    if not isinstance(loaded, dict):
        raise ConfigurationError("Configuration must be a YAML mapping")

    data: dict[str, object] = {str(k): v for k, v in loaded.items()}
    _apply_environment(data, os.environ if environ is None else environ)
    base = path.resolve().parent

    version = _get(data, "version", int, "root", default=SUPPORTED_VERSION)
    input_section = _section(data, "input")
    output_section = _section(data, "output")
    processing = _section(data, "processing")
    logging_section = data.get("logging")
    log_data = _section(data, "logging") if logging_section is not None else {}

    minimum = processing.get("minimum_value", 0)

    if isinstance(minimum, bool) or not isinstance(minimum, (int, float)):
        raise ConfigurationError("'processing.minimum_value' must be a number")

    return AppConfig(
        version=version,
        input=InputConfig(
            path=_resolve(_get(input_section, "path", str, "input"), base),
            format=_get(input_section, "format", str, "input", "auto"),
        ),
        output=OutputConfig(
            path=_resolve(_get(output_section, "path", str, "output"), base),
            format=_get(output_section, "format", str, "output", "auto"),
            backup_existing=_get(
                output_section, "backup_existing", bool, "output", False
            ),
            summary_path=_optional_path(
                output_section, "summary_path", "output", base
            ),
        ),
        processing=ProcessingConfig(
            skip_invalid=_get(processing, "skip_invalid", bool, "processing"),
            minimum_value=float(minimum),
            allowed_types=_string_list(processing, "allowed_types", "processing"),
            allowed_manufacturers=_string_list(
                processing, "allowed_manufacturers", "processing"
            ),
            allowed_statuses=(
                _string_list(processing, "allowed_statuses", "processing")
                if processing.get("allowed_statuses") is not None
                else DEFAULT_STATUSES
            ),
        ),
        logging=LoggingConfig(
            level=str(_get(log_data, "level", str, "logging", "INFO")).upper(),
            path=_optional_path(log_data, "path", "logging", base),
            errors_path=_optional_path(log_data, "errors_path", "logging", base),
            max_bytes=_get(log_data, "max_bytes", int, "logging", 1_048_576),
            backup_count=_get(log_data, "backup_count", int, "logging", 3),
        ),
    )


def _check_output_directory(path: Path) -> None:
    """The directory is created later, but it must be creatable."""
    ancestor = path.parent

    while not ancestor.exists() and ancestor != ancestor.parent:
        ancestor = ancestor.parent

    if not ancestor.is_dir():
        raise ConfigurationError(
            f"Output directory cannot be created: {ancestor} is not a directory"
        )


def validate_config(config: AppConfig) -> None:
    """Fail fast: detect incorrect configuration before any processing."""
    if config.version != SUPPORTED_VERSION:
        raise ConfigurationError(
            f"Unsupported configuration version: {config.version}"
        )

    if config.input.format not in INPUT_FORMATS:
        raise ConfigurationError(f"Unsupported input format: {config.input.format}")

    if config.output.format not in OUTPUT_FORMATS:
        raise ConfigurationError(
            f"Unsupported output format: {config.output.format}"
        )

    if config.processing.minimum_value < 0:
        raise ConfigurationError("minimum_value must not be negative")

    if not config.processing.allowed_types:
        raise ConfigurationError("allowed_types must not be empty")

    if not config.processing.allowed_manufacturers:
        raise ConfigurationError("allowed_manufacturers must not be empty")

    if not config.processing.allowed_statuses:
        raise ConfigurationError("allowed_statuses must not be empty")

    if config.logging.level not in LOG_LEVELS:
        raise ConfigurationError(f"Unknown log level: {config.logging.level}")

    if config.logging.max_bytes <= 0 or config.logging.backup_count < 0:
        raise ConfigurationError("Invalid log rotation settings")

    if not config.input.path.is_file():
        raise ConfigurationError(f"Input file does not exist: {config.input.path}")

    _check_output_directory(config.output.path)

    if config.output.summary_path is not None:
        _check_output_directory(config.output.summary_path)


def load_and_validate(
    path: Path,
    environ: Mapping[str, str] | None = None,
) -> AppConfig:
    config = load_config(path, environ)
    validate_config(config)

    return config

