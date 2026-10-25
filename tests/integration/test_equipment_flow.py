"""Integration tests: several real components, real temporary files."""

import csv
import json
import sys
from asyncio import run
from collections.abc import Callable, Iterator
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from equipment_manager.domain.adapters import JsonReportFormatter
from equipment_manager.domain.container import build_container
from equipment_manager.domain.dto import (
    ComputerPayload,
    DevicePayload,
    GenericPayload,
    PrinterPayload,
    device_from_payload,
)
from equipment_manager.domain.models import DeviceStatus
from equipment_manager.domain.sync import InventorySyncService
from equipment_manager.importer.config import (
    AppConfig,
    InputConfig,
    LoggingConfig,
    OutputConfig,
    ProcessingConfig,
    load_and_validate,
)
from equipment_manager.importer.exceptions import (
    DataExportError,
    RecordValidationError,
)
from equipment_manager.importer.exporters import JsonExporter
from equipment_manager.importer.main import main
from equipment_manager.importer.models import EquipmentRecord
from equipment_manager.importer.services import ImportStatistics, run_import
from equipment_manager.importer.utils import atomic_writer

pytestmark = pytest.mark.integration

PROJECT = Path(__file__).resolve().parents[2]
HEADER = "inventory_number,type,manufacturer,model,value,status\n"
CSV_TEXT = (
    HEADER
    + "PC-001,Laptop,Lenovo,ThinkPad E14,28500.00,in_use\n"
    + "PC-002,Laptop,Dell,Latitude 5440,36900.00,in_repair\n"
    + "PC-003,Monitor,Dell,U2723QE,17200.50,\n"
    + "PC-004,Printer,HP,LaserJet M111w,4800,in_storage\n"
    + "PC-005,Laptop,Lenovo,IdeaPad 3,not-a-number,in_use\n"  # malformed value
    + "PC-006,Router,TP-Link,Archer AX55,3100,lost\n"  # status not allowed
    + "PC-007,Server,HP,ProLiant DL20,74500,in_use\n"
    + "PC-008,Laptop,Dell,XPS 13\n"  # short record
)


def make_config(
    directory: Path, source: Path, *, skip_invalid: bool = True
) -> AppConfig:
    return AppConfig(
        version=1,
        input=InputConfig(source),
        output=OutputConfig(directory / "out" / "equipment.json"),
        processing=ProcessingConfig(
            skip_invalid=skip_invalid,
            minimum_value=0.0,
            allowed_types=("Laptop", "Monitor", "Printer", "Router", "Server"),
            allowed_manufacturers=("Lenovo", "Dell", "HP", "TP-Link"),
            allowed_statuses=("in_use", "in_storage", "in_repair", "decommissioned"),
        ),
        logging=LoggingConfig(errors_path=directory / "logs" / "errors.csv"),
    )


@pytest.fixture
def equipment_csv(csv_writer: Callable[[str, str], Path]) -> Path:
    return csv_writer("equipment.csv", CSV_TEXT)


def record_to_payload(item: dict[str, object]) -> DevicePayload:
    """Adapter used by the flow: exported JSON record -> provider payload."""
    number = str(item["inventory_number"])
    manufacturer = str(item["manufacturer"])
    model = str(item["model"])
    cost = float(str(item["value"]))
    status = str(item["status"])

    if item["type"] == "Laptop":
        return ComputerPayload(
            kind="computer", inventory_number=number, manufacturer=manufacturer,
            model=model, cost=cost, purchased_on="2025-01-15", status=status,
            cpu="n/a", ram_gb=8, storage_gb=256,
        )

    if item["type"] == "Printer":
        return PrinterPayload(
            kind="printer", inventory_number=number, manufacturer=manufacturer,
            model=model, cost=cost, purchased_on="2025-01-15", status=status,
            technology="laser", pages_per_minute=20,
        )

    return GenericPayload(
        kind="device", inventory_number=number, manufacturer=manufacturer,
        model=model, cost=cost, purchased_on="2025-01-15", status=status,
    )


# ----------------------------------------------- 1. CSV -> validation -> JSON
def test_csv_import_to_json_export_in_tolerant_mode(
    tmp_path: Path, equipment_csv: Path
) -> None:
    config = make_config(tmp_path, equipment_csv)

    statistics = run_import(config)

    assert statistics.as_dict() == {
        "total": 8, "valid": 5, "invalid": 3, "filtered": 0, "exported": 5,
    }
    exported = json.loads(config.output.path.read_text(encoding="utf-8"))
    assert [item["inventory_number"] for item in exported] == [
        "PC-001", "PC-002", "PC-003", "PC-004", "PC-007",
    ]
    assert {item["inventory_number"]: item["status"] for item in exported} == {
        "PC-001": "in_use", "PC-002": "in_repair", "PC-003": "in_use",
        "PC-004": "in_storage", "PC-007": "in_use",
    }


def test_malformed_records_are_written_to_the_error_log(
    tmp_path: Path, equipment_csv: Path
) -> None:
    config = make_config(tmp_path, equipment_csv)

    run_import(config)

    assert config.logging.errors_path is not None
    rows = list(csv.DictReader(config.logging.errors_path.open(encoding="utf-8", newline="")))
    assert [(r["line_number"], r["field"]) for r in rows] == [
        ("6", "value"), ("7", "status"), ("9", "value"),
    ]


def test_strict_mode_stops_and_creates_no_output(
    tmp_path: Path, equipment_csv: Path
) -> None:
    config = make_config(tmp_path, equipment_csv, skip_invalid=False)
    statistics = ImportStatistics()

    with pytest.raises(RecordValidationError) as exc_info:
        run_import(config, statistics=statistics)

    assert exc_info.value.line_number == 6
    assert statistics.valid == 4 and statistics.invalid == 1
    assert not config.output.path.exists()


# --------------------------------------------- 2. configuration + CLI run
def write_yaml(tmp_path: Path, *, skip: str = "true") -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(
        "input:\n  path: equipment.csv\n"
        "output:\n  path: out/equipment.json\n  summary_path: out/summary.json\n"
        f"processing:\n  skip_invalid: {skip}\n"
        "  allowed_types: [Laptop, Monitor, Printer, Router, Server]\n"
        "  allowed_manufacturers: [Lenovo, Dell, HP, TP-Link]\n"
        "logging:\n  errors_path: logs/errors.csv\n",
        encoding="utf-8",
    )

    return path


def test_yaml_configuration_drives_the_whole_run(
    tmp_path: Path, equipment_csv: Path
) -> None:
    main(["--config", str(write_yaml(tmp_path))])

    summary = json.loads((tmp_path / "out" / "summary.json").read_text(encoding="utf-8"))
    assert summary["exported"] == 5
    assert (tmp_path / "logs" / "errors.csv").exists()


def test_environment_variable_switches_to_strict_mode(
    tmp_path: Path, equipment_csv: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = write_yaml(tmp_path)
    monkeypatch.setenv("IMPORTER_SKIP_INVALID", "false")

    with pytest.raises(SystemExit) as exc_info:
        main(["--config", str(config_path)])

    assert exc_info.value.code == 1
    assert not (tmp_path / "out" / "equipment.json").exists()


def test_invalid_configuration_stops_before_any_processing(
    tmp_path: Path,
) -> None:
    config_path = write_yaml(tmp_path)  # equipment.csv does not exist

    with pytest.raises(SystemExit) as exc_info:
        main(["--config", str(config_path)])

    assert exc_info.value.code == 1
    assert not (tmp_path / "out").exists()


# ------------------------------------- 3. import -> registry -> maintenance
def test_full_equipment_flow_from_csv_to_report(
    tmp_path: Path, equipment_csv: Path, notifier: Mock, today: object
) -> None:
    config = make_config(tmp_path, equipment_csv)
    run_import(config)
    exported = json.loads(config.output.path.read_text(encoding="utf-8"))

    container = build_container(
        notifier=notifier, formatter=JsonReportFormatter(indent=2)
    )
    for item in exported:
        container.registry.register(device_from_payload(record_to_payload(item)))
    container.registry["PC-002"].change_status(DeviceStatus.DECOMMISSIONED)
    container.registry["PC-001"].change_status(DeviceStatus.IN_REPAIR)

    sent = container.maintenance.notify_due(today)  # type: ignore[arg-type]
    report = json.loads(container.reports.render())

    assert len(container.registry) == 5
    assert sent == 4  # the decommissioned PC-002 is skipped
    assert notifier.send.call_count == 4
    assert report["total_devices"] == 5
    assert report["total_cost"]["amount"] == "161900.50"
    assert report["most_expensive"].startswith("PC-007")
    report_file = tmp_path / "report.json"
    with atomic_writer(report_file) as file:
        file.write(json.dumps(report))
    assert json.loads(report_file.read_text(encoding="utf-8")) == report


# ------------------------------------------------- 4. async provider flow
def test_async_provider_to_report_flow(
    notifier: Mock, today: object, equipment_csv: Path, tmp_path: Path
) -> None:
    config = make_config(tmp_path, equipment_csv)
    run_import(config)
    exported = json.loads(config.output.path.read_text(encoding="utf-8"))
    provider = AsyncMock()
    provider.fetch_devices.return_value = [record_to_payload(i) for i in exported]
    container = build_container(notifier=notifier)

    result = run(InventorySyncService(provider, container.registry).sync())
    run(InventorySyncService(provider, container.registry).sync())  # repeat is safe

    assert result.added == 5
    assert len(container.registry) == 5
    assert provider.fetch_devices.await_count == 2
    assert container.maintenance.notify_due(today) == 5  # type: ignore[arg-type]


# ------------------------------------------------------ 5. atomic failure
def test_failure_during_export_keeps_old_output_and_leaves_no_temp_files(
    tmp_path: Path, equipment_csv: Path
) -> None:
    config = make_config(tmp_path, equipment_csv)
    run_import(config)
    before = config.output.path.read_bytes()

    class FailingExporter:
        def write(self, records: Iterator[EquipmentRecord], path: Path) -> int:
            def broken() -> Iterator[EquipmentRecord]:
                yield next(iter(records))
                raise OSError("disk full")

            return JsonExporter().write(broken(), path)

    with pytest.raises(DataExportError):
        run_import(config, exporter=FailingExporter())  # type: ignore[arg-type]

    assert config.output.path.read_bytes() == before
    assert sorted(p.name for p in config.output.path.parent.iterdir()) == ["equipment.json"]


# ------------------------------------------------- 6. tmp_path isolation
def snapshot(root: Path) -> set[str]:
    return {
        str(p.relative_to(root))
        for p in root.rglob("*")
        if ".git" not in p.parts and "__pycache__" not in p.parts
        and ".pytest_cache" not in p.parts and ".mypy_cache" not in p.parts
        and ".ruff_cache" not in p.parts and ".hypothesis" not in p.parts
        and "htmlcov" not in p.parts and ".venv" not in p.parts
        and not p.name.startswith(".coverage") and "egg-info" not in str(p)
    }


def test_flows_do_not_write_into_the_repository(
    tmp_path: Path, equipment_csv: Path
) -> None:
    before = snapshot(PROJECT)

    run_import(make_config(tmp_path, equipment_csv))
    main(["--config", str(write_yaml(tmp_path))])

    assert snapshot(PROJECT) == before


def test_shipped_configuration_and_sample_data_work_together(tmp_path: Path) -> None:
    config = load_and_validate(PROJECT / "config.yaml", environ={})
    isolated = replace(
        config,
        output=OutputConfig(tmp_path / "equipment.json"),
        logging=LoggingConfig(errors_path=tmp_path / "errors.csv"),
    )

    statistics = run_import(isolated)

    assert statistics.total == 16 and statistics.valid == 10


_ = sys
