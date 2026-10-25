"""Tests added after the first coverage report (see report, section 8).

Each test covers an execution path that had no test before.
"""

import sys
from pathlib import Path

import pytest

from equipment_manager import analytics, processors
from equipment_manager.data import DEVICES
from equipment_manager.domain.models import Manufacturer
from equipment_manager.domain.value_objects import Money
from equipment_manager.importer.config import load_config
from equipment_manager.importer.exceptions import ConfigurationError, DataImportError
from equipment_manager.importer.readers import JsonImporter, JsonLinesImporter
from equipment_manager.main import main, run_analysis, run_demo
from equipment_manager.streaming.experiment import EarlyTerminationResult
from equipment_manager.streaming.filters import ValidationStats, validate_devices


# --------------------------------------------------------- empty collections
def test_lab2_functions_handle_empty_input() -> None:
    assert analytics.find_most_expensive([]) is None
    assert analytics.calculate_cost_range([]) == (0.0, 0.0)
    assert analytics.calculate_average_cost([]) == 0.0
    assert processors.get_unique_types([]) == set()
    assert processors.find_linear([], "PC-001") is None


def test_unique_types_of_sample_data() -> None:
    assert processors.get_unique_types(DEVICES) == {
        "Laptop", "Monitor", "Printer", "Router", "Server", "Keyboard",
    }


def test_analysis_demo_survives_an_empty_catalog(
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_analysis([])

    out = capsys.readouterr().out
    assert "Total cost: 0.00" in out
    assert "Most expensive" not in out


def test_demo_without_the_searched_device(
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_demo([])

    assert "Device found" not in capsys.readouterr().out


# ------------------------------------------------------------ value objects
def test_manufacturer_str_is_the_name() -> None:
    assert str(Manufacturer("Dell", "USA")) == "Dell"


def test_money_cannot_be_compared_with_a_number() -> None:
    with pytest.raises(TypeError):
        _ = Money.of(1) < 5


# ------------------------------------------------------------ configuration
BASE = (
    "input:\n  path: a.csv\noutput:\n  path: b.json\n"
    "processing:\n{skip}  allowed_types: [Laptop]\n  allowed_manufacturers: [Dell]\n"
)


def test_missing_required_key_is_reported_with_its_path(tmp_path: Path) -> None:
    path = tmp_path / "c.yaml"
    path.write_text(BASE.format(skip=""), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="processing.skip_invalid"):
        load_config(path)


def test_environment_override_of_a_non_mapping_section(tmp_path: Path) -> None:
    path = tmp_path / "c.yaml"
    path.write_text("processing: 5\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="must be a mapping"):
        load_config(path, environ={"IMPORTER_SKIP_INVALID": "true"})


def test_configuration_with_invalid_encoding(tmp_path: Path) -> None:
    path = tmp_path / "c.yaml"
    path.write_bytes(b"input: \xff\xfe\n")

    with pytest.raises(ConfigurationError, match="Cannot read") as exc_info:
        load_config(path)

    assert isinstance(exc_info.value.__cause__, UnicodeDecodeError)


# ----------------------------------------------------------------- readers
@pytest.mark.parametrize("importer", [JsonImporter(), JsonLinesImporter()])
def test_json_readers_report_unreadable_files(
    tmp_path: Path, importer: JsonImporter | JsonLinesImporter
) -> None:
    path = tmp_path / "data.json"
    path.write_bytes(b"\xff\xfe\xfa")

    with pytest.raises(DataImportError, match="Cannot read file"):
        list(importer.read(path))


# ---------------------------------------------------------------- streaming
def test_stream_validation_rejects_non_finite_costs() -> None:
    rows = [
        {"inventory_number": "PC-1", "type": "Laptop", "manufacturer": "Dell", "model": "X", "cost": text}
        for text in ("nan", "inf", "-inf", "10")
    ]
    stats = ValidationStats()

    valid = list(validate_devices(rows, stats))

    assert len(valid) == 1
    assert (stats.valid, stats.invalid) == (1, 3)


# ---------------------------------------------------------------- root CLI
def test_experiment_flag_with_replaced_slow_function(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[str] = []

    def fast_early_termination() -> EarlyTerminationResult:
        calls.append("early")
        return EarlyTerminationResult(10, 0.001, 0.002, None, 0)

    monkeypatch.setattr(
        "equipment_manager.main.run_early_termination", fast_early_termination
    )
    monkeypatch.setattr(sys, "argv", ["equipment-manager", "--experiment", "--sizes", "50"])

    main()

    out = capsys.readouterr().out
    assert calls == ["early"]
    assert "Eager vs lazy processing" in out
    assert "Find the first expensive server in 10 records" in out
