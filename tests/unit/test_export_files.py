"""File export tests: tmp_path, atomic output, context managers, chaining."""

import csv
import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from equipment_manager.importer.exceptions import (
    DataExportError,
    RecordValidationError,
)
from equipment_manager.importer.exporters import JsonExporter, JsonLinesExporter
from equipment_manager.importer.models import EquipmentRecord
from equipment_manager.importer.reports import ErrorReport
from equipment_manager.importer.utils import (
    atomic_writer,
    logged_operation,
    temporary_path,
)


def records(count: int) -> list[EquipmentRecord]:
    return [
        EquipmentRecord(f"PC-{n:03d}", "Laptop", "Dell", "XPS", 100.0 * n)
        for n in range(1, count + 1)
    ]


def failing_stream(good: int) -> Iterator[EquipmentRecord]:
    yield from records(good)
    raise OSError("disk full")


# ----------------------------------------------------------------- tmp_path
def test_json_export_writes_a_valid_document(tmp_path: Path) -> None:
    target = tmp_path / "out" / "equipment.json"

    count = JsonExporter().write(records(3), target)

    data = json.loads(target.read_text(encoding="utf-8"))
    assert count == 3
    assert [item["inventory_number"] for item in data] == ["PC-001", "PC-002", "PC-003"]
    assert data[0] == {
        "inventory_number": "PC-001", "type": "Laptop", "manufacturer": "Dell",
        "model": "XPS", "value": 100.0, "status": "in_use",
    }


def test_export_keeps_non_ascii_text(tmp_path: Path) -> None:
    target = tmp_path / "ua.json"
    item = EquipmentRecord("PC-001", "Laptop", "Dell", "Ноутбук", 1.0)

    JsonExporter().write([item], target)

    assert "Ноутбук" in target.read_text(encoding="utf-8")


def test_empty_export_is_a_valid_empty_array(tmp_path: Path) -> None:
    target = tmp_path / "empty.json"

    assert JsonExporter().write([], target) == 0
    assert json.loads(target.read_text(encoding="utf-8")) == []


def test_jsonl_export_has_one_object_per_line(tmp_path: Path) -> None:
    target = tmp_path / "equipment.jsonl"

    JsonLinesExporter().write(records(2), target)

    lines = target.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["inventory_number"] for line in lines] == ["PC-001", "PC-002"]


def test_each_test_gets_its_own_directory(tmp_path: Path) -> None:
    assert list(tmp_path.iterdir()) == []


# ----------------------------------------------------------- atomic output
def test_failed_export_keeps_the_previous_file(tmp_path: Path) -> None:
    target = tmp_path / "result.json"
    target.write_text("old valid data", encoding="utf-8")

    with pytest.raises(DataExportError):
        JsonExporter().write(failing_stream(2), target)

    assert target.read_text(encoding="utf-8") == "old valid data"
    assert not temporary_path(target).exists()


def test_failed_first_export_leaves_no_files(tmp_path: Path) -> None:
    target = tmp_path / "result.json"

    with pytest.raises(DataExportError):
        JsonExporter().write(failing_stream(1), target)

    assert list(tmp_path.iterdir()) == []


def test_os_error_is_chained_to_export_error(tmp_path: Path) -> None:
    with pytest.raises(DataExportError) as exc_info:
        JsonExporter().write(failing_stream(0), tmp_path / "r.json")

    assert isinstance(exc_info.value.__cause__, OSError)
    assert str(exc_info.value.__cause__) == "disk full"


def test_serialization_error_becomes_export_error(tmp_path: Path) -> None:
    bad = EquipmentRecord("PC-001", "Laptop", "Dell", "XPS", 1.0)
    object.__setattr__(bad, "model", object())
    target = tmp_path / "r.json"

    with pytest.raises(DataExportError, match="serializable") as exc_info:
        JsonExporter().write([bad], target)

    assert isinstance(exc_info.value.__cause__, TypeError)
    assert not target.exists()


def test_export_to_a_directory_path_fails_cleanly(tmp_path: Path) -> None:
    target = tmp_path / "result.json"
    target.mkdir()

    with pytest.raises(DataExportError):
        JsonExporter().write(records(1), target)

    assert not temporary_path(target).exists()


def test_backup_of_the_previous_output(tmp_path: Path) -> None:
    target = tmp_path / "result.json"
    JsonExporter().write(records(1), target)
    first = target.read_text(encoding="utf-8")

    JsonExporter(backup=True).write(records(2), target)

    assert (tmp_path / "result.json.bak").read_text(encoding="utf-8") == first
    assert len(json.loads(target.read_text(encoding="utf-8"))) == 2


# ----------------------------------------------- context manager cleanup
def test_atomic_writer_commits_on_success(tmp_path: Path) -> None:
    target = tmp_path / "x.txt"

    with atomic_writer(target) as file:
        file.write("data")
        assert temporary_path(target).exists()
        assert not target.exists()

    assert target.read_text(encoding="utf-8") == "data"
    assert not temporary_path(target).exists()


def test_atomic_writer_cleans_up_on_exception_in_the_body(tmp_path: Path) -> None:
    target = tmp_path / "x.txt"

    with pytest.raises(RuntimeError, match="boom"), atomic_writer(target) as file:
        file.write("partial")
        raise RuntimeError("boom")

    assert not target.exists()
    assert not temporary_path(target).exists()


def test_error_report_file_is_closed_after_exception(tmp_path: Path) -> None:
    path = tmp_path / "errors.csv"
    report = ErrorReport(path)

    with pytest.raises(ValueError), report:
        report.record(RecordValidationError("bad", line_number=3, field="value"))
        raise ValueError("stop")

    assert report._file is None
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    assert rows == [{"line_number": "3", "field": "value", "message": "bad", "value": ""}]


def test_error_report_without_path_only_counts() -> None:
    with ErrorReport(None) as report:
        report.record(RecordValidationError("x"))
        report.record(RecordValidationError("y"))

    assert report.count == 2


def test_logged_operation_logs_success(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    with logged_operation("Export"):
        pass

    assert [r.getMessage()[:15] for r in caplog.records] == ["Export started", "Export finished"]


def test_logged_operation_logs_failure_and_reraises(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    with pytest.raises(KeyError), logged_operation("Export"):
        raise KeyError("missing")

    assert any("Export failed" in r.getMessage() for r in caplog.records)
    assert caplog.records[-1].exc_info is not None
