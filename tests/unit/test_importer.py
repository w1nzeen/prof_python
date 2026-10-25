import csv
import json
import logging
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

from equipment_manager.exceptions import EquipmentError
from equipment_manager.importer import experiments as exp
from equipment_manager.importer.config import (
    AppConfig,
    load_and_validate,
    load_config,
    validate_config,
)
from equipment_manager.importer.exceptions import (
    ApplicationError,
    ConfigurationError,
    DataError,
    DataExportError,
    DataImportError,
    DataValidationError,
    RecordValidationError,
)
from equipment_manager.importer.exporters import (
    JsonExporter,
    JsonLinesExporter,
    get_exporter,
)
from equipment_manager.importer.logging_config import (
    configure_logging,
    shutdown_logging,
)
from equipment_manager.importer.main import main
from equipment_manager.importer.models import (
    EXTRA_FIELDS_KEY,
    EquipmentRecord,
    RawRecord,
)
from equipment_manager.importer.readers import (
    CsvImporter,
    JsonImporter,
    JsonLinesImporter,
    detect_format,
)
from equipment_manager.importer.reports import ErrorReport
from equipment_manager.importer.services import (
    ImportStatistics,
    filter_by_value,
    import_records,
    run_import,
)
from equipment_manager.importer.utils import (
    atomic_writer,
    logged_operation,
    temporary_path,
)
from equipment_manager.importer.validators import (
    ValidationRules,
    validate_record,
)

RULES = ValidationRules.from_lists(exp.TYPES, exp.MANUFACTURERS)
HEADER = ",".join(exp.HEADER)
PROJECT = Path(__file__).resolve().parents[2]


def raw(**fields: object) -> RawRecord:
    data: dict[str, object] = {
        "inventory_number": "PC-001",
        "type": "Laptop",
        "manufacturer": "Dell",
        "model": "XPS 13",
        "value": "100",
    }
    data.update(fields)

    return RawRecord(2, data)


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")

    return path


def records(count: int) -> Iterator[EquipmentRecord]:
    for number in range(1, count + 1):
        yield EquipmentRecord(f"PC-{number:03d}", "Laptop", "Dell", "X", 1.0)


# ----------------------------------------------------------- exceptions
def test_exception_hierarchy() -> None:
    assert issubclass(ConfigurationError, ApplicationError)
    assert issubclass(DataError, ApplicationError)
    assert issubclass(DataValidationError, DataError)
    assert issubclass(RecordValidationError, DataValidationError)
    assert issubclass(DataImportError, DataError)
    assert issubclass(DataExportError, DataError)
    assert issubclass(ApplicationError, EquipmentError)

    error = RecordValidationError("bad", line_number=5, field="value", value="x")
    assert (str(error), error.line_number, error.field, error.value) == (
        "bad", 5, "value", "x",
    )


# ----------------------------------------------------------- validation
def test_validate_valid_record_and_normalization() -> None:
    record = validate_record(
        raw(inventory_number=" pc-007 ", type="laptop", manufacturer="DELL", value="1 000".replace(" ", "")),
        RULES,
    )
    assert record == EquipmentRecord("PC-007", "Laptop", "Dell", "XPS 13", 1000.0)
    assert validate_record(raw(value="12,5"), RULES).value == 12.5
    assert validate_record(raw(value=0), RULES).value == 0.0
    assert validate_record(raw(value=3), RULES).value == 3.0


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"inventory_number": "12"}, "inventory_number"),
        ({"inventory_number": ""}, "inventory_number"),
        ({"type": "Tablet"}, "type"),
        ({"manufacturer": "Apple"}, "manufacturer"),
        ({"model": "  "}, "model"),
        ({"model": "x" * 101}, "model"),
        ({"value": "abc"}, "value"),
        ({"value": "-1"}, "value"),
        ({"value": "nan"}, "value"),
        ({"value": "inf"}, "value"),
        ({"value": True}, "value"),
        ({"value": None}, "value"),
    ],
)
def test_validate_rejects(changes: dict[str, object], field: str) -> None:
    with pytest.raises(RecordValidationError) as info:
        validate_record(raw(**changes), RULES)

    assert info.value.field == field
    assert info.value.line_number == 2


def test_validate_structure_errors() -> None:
    with pytest.raises(RecordValidationError):
        validate_record(RawRecord(3, {"inventory_number": "PC-1"}), RULES)

    with pytest.raises(RecordValidationError, match="more fields"):
        validate_record(raw(**{EXTRA_FIELDS_KEY: ["x"]}), RULES)


def test_exception_chaining_keeps_cause() -> None:
    with pytest.raises(RecordValidationError) as info:
        validate_record(raw(value="wrong"), RULES)

    assert isinstance(info.value.__cause__, ValueError)


# -------------------------------------------------------------- readers
def test_csv_importer_streams_with_line_numbers(tmp_path: Path) -> None:
    path = write(tmp_path / "a.csv", HEADER + "\nPC-001,Laptop,Dell,X,1\n\nPC-002,Laptop,Dell,X,2\n")
    reader = CsvImporter().read(path)
    first = next(reader)  # a generator: nothing is read in advance

    assert (first.line_number, first.data["inventory_number"]) == (2, "PC-001")
    assert [r.line_number for r in reader] == [4]


def test_csv_importer_errors(tmp_path: Path) -> None:
    with pytest.raises(DataImportError) as info:
        list(CsvImporter().read(tmp_path / "missing.csv"))

    assert isinstance(info.value.__cause__, FileNotFoundError)

    with pytest.raises(DataImportError, match="empty"):
        list(CsvImporter().read(write(tmp_path / "e.csv", "")))

    with pytest.raises(DataImportError, match="Missing columns"):
        list(CsvImporter().read(write(tmp_path / "h.csv", "a,b\n1,2\n")))

    bad = tmp_path / "bad.csv"
    bad.write_bytes(HEADER.encode() + b"\nPC-1,Laptop,Dell,\xff\xfe,1\n")
    with pytest.raises(DataImportError):
        list(CsvImporter().read(bad))


def test_csv_bom_and_short_and_long_rows(tmp_path: Path) -> None:
    path = tmp_path / "bom.csv"
    path.write_bytes(
        b"\xef\xbb\xbf" + (HEADER + "\nPC-1,Laptop,Dell,X\nPC-2,Laptop,Dell,X,1,9\n").encode()
    )
    rows = list(CsvImporter().read(path))

    assert rows[0].data["value"] is None
    assert EXTRA_FIELDS_KEY in rows[1].data


def test_json_and_jsonl_importers(tmp_path: Path) -> None:
    items = [{"inventory_number": "PC-1"}, {"inventory_number": "PC-2"}]
    array = write(tmp_path / "a.json", json.dumps(items))
    lines = write(tmp_path / "a.jsonl", "\n".join(json.dumps(i) for i in items) + "\n\n")

    assert [r.data["inventory_number"] for r in JsonImporter().read(array)] == ["PC-1", "PC-2"]
    assert [r.line_number for r in JsonLinesImporter().read(lines)] == [1, 2]
    assert [r.data for r in JsonImporter().read(write(tmp_path / "b.json", "[1]"))] == [{}]

    with pytest.raises(DataImportError, match="array"):
        list(JsonImporter().read(write(tmp_path / "c.json", "{}")))

    with pytest.raises(DataImportError) as info:
        list(JsonImporter().read(write(tmp_path / "d.json", "[")))
    assert isinstance(info.value.__cause__, json.JSONDecodeError)

    with pytest.raises(DataImportError, match="line 2"):
        list(JsonLinesImporter().read(write(tmp_path / "e.jsonl", '{"a": 1}\n{oops\n')))


def test_detect_format() -> None:
    assert detect_format(Path("x.CSV")) == "csv"
    assert detect_format(Path("x.ndjson")) == "jsonl"
    assert detect_format(Path("x.txt"), "csv") == "csv"

    with pytest.raises(DataImportError):
        detect_format(Path("x.txt"))


# ------------------------------------------------- services / policies
def make_input(tmp_path: Path, valid: int = 20, invalid: int = 2) -> Path:
    path = tmp_path / "input.csv"
    exp.generate_csv(path, valid=valid, invalid=invalid)

    return path


def test_tolerant_mode_counts_and_skips(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    statistics = ImportStatistics()
    caplog.set_level(logging.WARNING)

    result = list(
        import_records(
            CsvImporter(), make_input(tmp_path), RULES,
            skip_invalid=True, statistics=statistics,
        )
    )

    assert len(result) == 20
    assert (statistics.total, statistics.valid, statistics.invalid) == (22, 20, 2)
    assert caplog.text.count("Invalid record at line") == 2


def test_strict_mode_stops_at_first_error(tmp_path: Path) -> None:
    statistics = ImportStatistics()
    stream = import_records(
        CsvImporter(), make_input(tmp_path), RULES,
        skip_invalid=False, statistics=statistics,
    )

    with pytest.raises(RecordValidationError):
        list(stream)

    assert statistics.invalid == 1 and statistics.total < 22


def test_filter_by_value() -> None:
    statistics = ImportStatistics()
    items = [
        EquipmentRecord("PC-1", "Laptop", "Dell", "X", 10.0),
        EquipmentRecord("PC-2", "Laptop", "Dell", "X", 99.0),
    ]
    kept = list(filter_by_value(items, 50.0, statistics))

    assert [r.inventory_number for r in kept] == ["PC-2"] and statistics.filtered == 1


def test_error_report_csv(tmp_path: Path) -> None:
    path = tmp_path / "logs" / "errors.csv"

    with ErrorReport(path) as report:
        report.record(RecordValidationError("Bad", line_number=7, field="value", value="x"))

    assert report.count == 1
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    assert rows == [{"line_number": "7", "field": "value", "message": "Bad", "value": "x"}]

    with ErrorReport(None) as nothing:
        nothing.record(RecordValidationError("ignored"))
    assert nothing.count == 1


def test_error_report_cannot_open(tmp_path: Path) -> None:
    blocker = write(tmp_path / "file", "x")

    with pytest.raises(DataExportError), ErrorReport(blocker / "errors.csv"):
        pass


# ------------------------------------------------------------ exporters
def test_json_and_jsonl_exporters(tmp_path: Path) -> None:
    target = tmp_path / "out" / "a.json"
    assert JsonExporter().write(records(3), target) == 3
    assert [r["inventory_number"] for r in json.loads(target.read_text(encoding="utf-8"))] == [
        "PC-001", "PC-002", "PC-003",
    ]

    assert JsonExporter().write(records(0), target) == 0
    assert json.loads(target.read_text(encoding="utf-8")) == []

    lines = tmp_path / "a.jsonl"
    assert JsonLinesExporter().write(records(2), lines) == 2
    assert len(lines.read_text(encoding="utf-8").splitlines()) == 2


def test_get_exporter() -> None:
    assert isinstance(get_exporter(Path("a.json")), JsonExporter)
    assert isinstance(get_exporter(Path("a.jsonl")), JsonLinesExporter)
    assert isinstance(get_exporter(Path("a.txt"), "json"), JsonExporter)

    with pytest.raises(DataExportError):
        get_exporter(Path("a.txt"))

    with pytest.raises(DataExportError):
        get_exporter(Path("a.json"), "xml")


def test_non_serializable_record_is_export_error(tmp_path: Path) -> None:
    bad = EquipmentRecord("PC-1", "Laptop", "Dell", "X", 1.0)
    object.__setattr__(bad, "model", object())
    target = tmp_path / "a.json"

    with pytest.raises(DataExportError) as info:
        JsonExporter().write([bad], target)

    assert isinstance(info.value.__cause__, TypeError)
    assert not target.exists() and not temporary_path(target).exists()


def test_atomic_writer_success_backup_and_failure(tmp_path: Path) -> None:
    target = tmp_path / "x.txt"

    with atomic_writer(target) as file:
        file.write("one")
    assert target.read_text(encoding="utf-8") == "one"

    with atomic_writer(target, backup=True) as file:
        file.write("two")
    assert target.read_text(encoding="utf-8") == "two"
    assert (tmp_path / "x.txt.bak").read_text(encoding="utf-8") == "one"

    with pytest.raises(RuntimeError), atomic_writer(target) as file:
        file.write("partial")
        raise RuntimeError("boom")
    assert target.read_text(encoding="utf-8") == "two"
    assert not temporary_path(target).exists()


def test_export_failure_keeps_previous_output(tmp_path: Path) -> None:
    target = tmp_path / "result.json"
    JsonExporter().write(records(2), target)
    before = target.read_bytes()

    with pytest.raises(DataExportError) as info:
        JsonExporter().write(exp.failing_records(after=2), target)

    assert isinstance(info.value.__cause__, OSError)
    assert target.read_bytes() == before
    assert not temporary_path(target).exists()


def test_strict_failure_does_not_create_output(tmp_path: Path) -> None:
    config = exp.make_config(tmp_path, make_input(tmp_path), skip_invalid=False)

    with pytest.raises(RecordValidationError):
        run_import(config)

    assert not config.output.path.exists()
    assert not temporary_path(config.output.path).exists()


# --------------------------------------------------------- run_import
def test_run_import_end_to_end(tmp_path: Path) -> None:
    config = exp.make_config(tmp_path, make_input(tmp_path), with_logs=True)
    statistics = run_import(config)

    assert statistics.as_dict() == {
        "total": 22, "valid": 20, "invalid": 2, "filtered": 0, "exported": 20,
    }
    assert len(json.loads(config.output.path.read_text(encoding="utf-8"))) == 20
    assert config.logging.errors_path is not None
    errors = list(csv.DictReader(config.logging.errors_path.open(encoding="utf-8", newline="")))
    assert len(errors) == 2


def test_run_import_jsonl_roundtrip_and_filter(tmp_path: Path) -> None:
    source = write(
        tmp_path / "in.jsonl",
        "\n".join(
            json.dumps({"inventory_number": f"PC-{i}", "type": "Laptop",
                        "manufacturer": "HP", "model": "M", "value": i * 10})
            for i in range(1, 6)
        ),
    )
    base = exp.make_config(tmp_path, source, output_name="out.jsonl")
    config = AppConfig(
        version=base.version, input=base.input, output=base.output,
        processing=type(base.processing)(True, 30.0, exp.TYPES, exp.MANUFACTURERS),
        logging=base.logging,
    )
    statistics = run_import(config)

    assert (statistics.filtered, statistics.exported) == (2, 3)
    assert len(config.output.path.read_text(encoding="utf-8").splitlines()) == 3


# ------------------------------------------------------------ context
def test_logged_operation(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)

    with logged_operation("Demo"):
        pass

    assert "Demo started" in caplog.text and "Demo finished in" in caplog.text

    with pytest.raises(ValueError), logged_operation("Broken"):
        raise ValueError("x")

    assert "Broken failed" in caplog.text


def test_configure_logging_rotating_file(tmp_path: Path) -> None:
    path = tmp_path / "logs" / "app.log"
    configure_logging("INFO", path, max_bytes=1000, backup_count=2)
    logging.getLogger("equipment_manager.importer.test").info("hello")
    shutdown_logging()

    assert "hello" in path.read_text(encoding="utf-8")


# -------------------------------------------------------------- config
def config_text(**overrides: str) -> str:
    return exp.valid_config_text(**overrides)


def test_load_config_relative_paths_and_defaults(tmp_path: Path) -> None:
    exp.generate_csv(tmp_path / "input.csv", valid=2)
    path = write(tmp_path / "c.yaml", config_text())
    config = load_and_validate(path, environ={})

    assert config.input.path == tmp_path / "input.csv"
    assert config.output.path == tmp_path / "out" / "result.json"
    assert config.processing.skip_invalid is True
    assert config.logging.level == "INFO" and config.logging.path is None


def test_environment_overrides(tmp_path: Path) -> None:
    exp.generate_csv(tmp_path / "input.csv", valid=2)
    path = write(tmp_path / "c.yaml", config_text())
    config = load_config(
        path,
        environ={
            "IMPORTER_SKIP_INVALID": "false",
            "IMPORTER_MINIMUM_VALUE": "5.5",
            "IMPORTER_LOG_LEVEL": "debug",
            "IMPORTER_OUTPUT_PATH": "x.json",
        },
    )

    assert config.processing.skip_invalid is False
    assert config.processing.minimum_value == 5.5
    assert config.logging.level == "DEBUG"
    assert config.output.path == tmp_path / "x.json"

    with pytest.raises(ConfigurationError):
        load_config(path, environ={"IMPORTER_SKIP_INVALID": "maybe"})

    with pytest.raises(ConfigurationError):
        load_config(path, environ={"IMPORTER_MINIMUM_VALUE": "abc"})


@pytest.mark.parametrize(
    "content",
    [
        "input: [unclosed",
        "- a\n- b\n",
        "input: 5\n",
        "output:\n  path: a\n",
        config_text() + "\nlogging: 3\n",
        config_text().replace("skip_invalid: true", "skip_invalid: 1"),
        config_text().replace("minimum_value: 0", "minimum_value: abc"),
        config_text().replace("allowed_types: [", "allowed_types: [1, "),
        config_text().replace("  allowed_types: [Laptop, Monitor, Printer, Router, Server, Keyboard]\n", ""),
        config_text() + "\nversion: [1]\n",
    ],
)
def test_load_config_errors(tmp_path: Path, content: str) -> None:
    with pytest.raises(ConfigurationError):
        load_config(write(tmp_path / "c.yaml", content), environ={})


def test_missing_configuration_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError) as info:
        load_config(tmp_path / "none.yaml")

    assert isinstance(info.value.__cause__, FileNotFoundError)


def test_validate_config_rules(tmp_path: Path) -> None:
    exp.generate_csv(tmp_path / "input.csv", valid=2)
    good = load_config(write(tmp_path / "c.yaml", config_text()), environ={})
    validate_config(good)

    bad_configs = [
        replace(good, version=2),
        replace(good, input=replace(good.input, format="xml")),
        replace(good, output=replace(good.output, format="xml")),
        replace(good, processing=replace(good.processing, minimum_value=-1.0)),
        replace(good, processing=replace(good.processing, allowed_types=())),
        replace(good, processing=replace(good.processing, allowed_manufacturers=())),
        replace(good, logging=replace(good.logging, level="LOUD")),
        replace(good, logging=replace(good.logging, max_bytes=0)),
        replace(good, input=replace(good.input, path=tmp_path / "missing.csv")),
        replace(
            good,
            output=replace(good.output, summary_path=tmp_path / "input.csv" / "s.json"),
        ),
    ]

    for config in bad_configs:
        with pytest.raises(ConfigurationError):
            validate_config(config)


# ---------------------------------------------------------------- main
def project_config(tmp_path: Path, skip: str = "true") -> Path:
    exp.generate_csv(tmp_path / "input.csv", valid=10, invalid=2)
    text = config_text().replace("skip_invalid: true", f"skip_invalid: {skip}")

    return write(tmp_path / "config.yaml", text + "logging:\n  path: logs/a.log\n  errors_path: logs/e.csv\n")


def test_main_success_and_logs(tmp_path: Path) -> None:
    main(["--config", str(project_config(tmp_path))])

    assert len(json.loads((tmp_path / "out" / "result.json").read_text(encoding="utf-8"))) == 10
    assert "Total=12, valid=10, invalid=2" in (tmp_path / "logs" / "a.log").read_text(encoding="utf-8")
    assert len((tmp_path / "logs" / "e.csv").read_text(encoding="utf-8").splitlines()) == 3


def test_main_exit_codes(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as strict:
        main(["--config", str(project_config(tmp_path, skip="false"))])
    assert strict.value.code == 1

    with pytest.raises(SystemExit) as missing:
        main(["--config", str(tmp_path / "nope.yaml")])
    assert missing.value.code == 1


def test_main_unexpected_error_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(config: AppConfig) -> ImportStatistics:
        raise ZeroDivisionError

    monkeypatch.setattr("equipment_manager.importer.main.run_import", explode)

    with pytest.raises(SystemExit) as info:
        main(["--config", str(project_config(tmp_path))])

    assert info.value.code == 2


def test_shipped_config_and_data_work(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = load_and_validate(PROJECT / "config.yaml", environ={})
    assert config.input.path == PROJECT / "data" / "equipment.csv"
    assert config.processing.skip_invalid is True

    statistics = run_import(exp.make_config(tmp_path, config.input.path))
    assert (statistics.total, statistics.valid, statistics.invalid) == (16, 10, 6)


# --------------------------------------------------------- experiments
def test_generate_csv_counts(tmp_path: Path) -> None:
    path = tmp_path / "g.csv"
    exp.generate_csv(path, valid=1000, invalid=10)
    statistics = ImportStatistics()
    list(import_records(CsvImporter(), path, RULES, skip_invalid=True, statistics=statistics))

    assert (statistics.valid, statistics.invalid) == (1000, 10)


def test_quick_experiments_run(capsys: pytest.CaptureFixture[str]) -> None:
    exp.main(["strict", "chaining", "atomic", "config"])
    out = capsys.readouterr().out

    assert "stopped at line" in out and "completed (exit 0)" in out
    assert "__cause__: ValueError" in out
    assert "Previous output intact: True" in out and "exit code = 1" in out
    assert "output directory is a file" in out

    with pytest.raises(SystemExit):
        exp.main(["unknown"])


def test_streaming_experiment_small(capsys: pytest.CaptureFixture[str]) -> None:
    exp.experiment_streaming_vs_eager((300, 600))
    assert "Streaming peak, MB" in capsys.readouterr().out
