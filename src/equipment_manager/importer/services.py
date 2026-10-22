"""Import use case: read -> validate -> filter -> export."""

import logging
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass
from pathlib import Path

from equipment_manager.importer.config import AppConfig
from equipment_manager.importer.exceptions import RecordValidationError
from equipment_manager.importer.exporters import Exporter, get_exporter
from equipment_manager.importer.models import EquipmentRecord
from equipment_manager.importer.readers import Importer, get_importer
from equipment_manager.importer.reports import (
    ErrorReport,
    SummaryTarget,
    write_summary,
)
from equipment_manager.importer.utils import logged_operation
from equipment_manager.importer.validators import (
    ValidationRules,
    validate_record,
)

logger = logging.getLogger(__name__)


@dataclass
class ImportStatistics:
    total: int = 0
    valid: int = 0
    invalid: int = 0
    filtered: int = 0
    exported: int = 0

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def import_records(
    importer: Importer,
    path: Path,
    rules: ValidationRules,
    *,
    skip_invalid: bool,
    statistics: ImportStatistics,
    error_report: ErrorReport | None = None,
) -> Iterator[EquipmentRecord]:
    """Lazily validate records.

    Tolerant mode (skip_invalid=True): log, count and skip.
    Strict mode: the first invalid record stops the import.
    """
    for raw in importer.read(path):
        statistics.total += 1

        try:
            record = validate_record(raw, rules)
        except RecordValidationError as error:
            statistics.invalid += 1

            if error_report is not None:
                error_report.record(error)

            if not skip_invalid:
                logger.error(
                    "Invalid record at line %s: %s", error.line_number, error
                )
                raise

            logger.warning(
                "Invalid record at line %s: %s", error.line_number, error
            )
            continue

        statistics.valid += 1
        yield record


def filter_by_value(
    records: Iterable[EquipmentRecord],
    minimum_value: float,
    statistics: ImportStatistics,
) -> Iterator[EquipmentRecord]:
    """Processing stage: drop records cheaper than the configured minimum."""
    for record in records:
        if record.value >= minimum_value:
            yield record
        else:
            statistics.filtered += 1


def run_import(
    config: AppConfig,
    *,
    importer: Importer | None = None,
    exporter: Exporter | None = None,
    statistics: ImportStatistics | None = None,
) -> ImportStatistics:
    """Run the whole pipeline; importer and exporter can be replaced.

    A caller may pass `statistics` to read the counters even when the
    import is interrupted by an exception (strict mode).
    """
    statistics = statistics if statistics is not None else ImportStatistics()
    rules = ValidationRules.from_lists(
        config.processing.allowed_types,
        config.processing.allowed_manufacturers,
    )
    used_importer = importer or get_importer(
        config.input.path, config.input.format
    )
    used_exporter = exporter or get_exporter(
        config.output.path,
        config.output.format,
        backup=config.output.backup_existing,
    )

    with logged_operation("Equipment import/export"):
        with ErrorReport(config.logging.errors_path) as error_report:
            records = import_records(
                used_importer,
                config.input.path,
                rules,
                skip_invalid=config.processing.skip_invalid,
                statistics=statistics,
                error_report=error_report,
            )
            selected = filter_by_value(
                records, config.processing.minimum_value, statistics
            )
            statistics.exported = used_exporter.write(
                selected, config.output.path
            )

        if config.output.summary_path is not None:
            write_summary(
                statistics.as_dict(),
                SummaryTarget(
                    config.output.summary_path,
                    backup=config.output.backup_existing,
                ),
            )

    logger.info(
        "Total=%s, valid=%s, invalid=%s, filtered=%s, exported=%s",
        statistics.total,
        statistics.valid,
        statistics.invalid,
        statistics.filtered,
        statistics.exported,
    )

    return statistics
