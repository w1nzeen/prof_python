"""Configuration tests: environment variables, allowed lists, YAML files."""

import os
from dataclasses import replace
from pathlib import Path

import pytest

from equipment_manager.importer.config import (
    DEFAULT_STATUSES,
    AppConfig,
    load_and_validate,
    load_config,
    validate_config,
)
from equipment_manager.importer.exceptions import ConfigurationError

BASE_YAML = """\
input:
  path: input.csv
output:
  path: out/result.json
processing:
  skip_invalid: true
  minimum_value: 0
  allowed_types: [Laptop, Printer]
  allowed_manufacturers: [Lenovo, HP]
"""


@pytest.fixture
def config_path(tmp_path: Path, csv_writer: object) -> Path:
    (tmp_path / "input.csv").write_text(
        "inventory_number,type,manufacturer,model,value\n", encoding="utf-8"
    )
    path = tmp_path / "config.yaml"
    path.write_text(BASE_YAML, encoding="utf-8")

    return path


@pytest.fixture
def config(config_path: Path) -> AppConfig:
    return load_and_validate(config_path)


# ------------------------------------------------- monkeypatch: environment
def test_environment_variable_overrides_yaml(
    config_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("IMPORTER_SKIP_INVALID", "false")
    monkeypatch.setenv("IMPORTER_LOG_LEVEL", "debug")

    config = load_config(config_path)  # reads the real os.environ

    assert config.processing.skip_invalid is False
    assert config.logging.level == "DEBUG"


def test_without_environment_yaml_values_are_used(
    config_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("IMPORTER_SKIP_INVALID", raising=False)

    assert load_config(config_path).processing.skip_invalid is True


def test_monkeypatch_restores_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMPORTER_LOG_LEVEL", "ERROR")

    assert os.environ["IMPORTER_LOG_LEVEL"] == "ERROR"


def test_environment_is_clean_in_the_next_test() -> None:
    assert "IMPORTER_LOG_LEVEL" not in os.environ


@pytest.mark.parametrize(
    ("text", "expected"),
    [("true", True), ("1", True), ("YES", True), ("on", True),
     ("false", False), ("0", False), ("No", False), ("off", False)],
)
def test_boolean_environment_values(
    config_path: Path, text: str, expected: bool
) -> None:
    config = load_config(config_path, environ={"IMPORTER_SKIP_INVALID": text})

    assert config.processing.skip_invalid is expected


@pytest.mark.parametrize(
    "environ",
    [
        {"IMPORTER_SKIP_INVALID": "maybe"},
        {"IMPORTER_MINIMUM_VALUE": "cheap"},
    ],
)
def test_invalid_environment_values(config_path: Path, environ: dict[str, str]) -> None:
    with pytest.raises(ConfigurationError, match="Environment variable"):
        load_config(config_path, environ=environ)


def test_environment_can_replace_paths(config_path: Path) -> None:
    config = load_config(
        config_path,
        environ={"IMPORTER_INPUT_PATH": "other.csv", "IMPORTER_OUTPUT_PATH": "o.json"},
    )

    assert config.input.path == config_path.parent / "other.csv"
    assert config.output.path == config_path.parent / "o.json"


def test_monkeypatch_chdir_does_not_change_config_resolution(
    config_path: Path, tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path_factory.mktemp("elsewhere"))

    config = load_config(config_path)

    assert config.input.path == config_path.parent / "input.csv"


# ------------------------------------------------ allowed lists and statuses
def test_allowed_lists_come_from_yaml(config: AppConfig) -> None:
    assert config.processing.allowed_types == ("Laptop", "Printer")
    assert config.processing.allowed_manufacturers == ("Lenovo", "HP")


def test_allowed_statuses_have_a_default(config: AppConfig) -> None:
    assert config.processing.allowed_statuses == DEFAULT_STATUSES


def test_allowed_statuses_can_be_configured(config_path: Path) -> None:
    config_path.write_text(
        BASE_YAML + "  allowed_statuses: [in_use, in_repair]\n", encoding="utf-8"
    )

    config = load_and_validate(config_path)

    assert config.processing.allowed_statuses == ("in_use", "in_repair")


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param(lambda c: replace(c, processing=replace(c.processing, allowed_types=())), id="no-types"),
        pytest.param(lambda c: replace(c, processing=replace(c.processing, allowed_manufacturers=())), id="no-manufacturers"),
        pytest.param(lambda c: replace(c, processing=replace(c.processing, allowed_statuses=())), id="no-statuses"),
        pytest.param(lambda c: replace(c, processing=replace(c.processing, minimum_value=-0.01)), id="negative-minimum"),
        pytest.param(lambda c: replace(c, version=2), id="unknown-version"),
        pytest.param(lambda c: replace(c, logging=replace(c.logging, level="LOUD")), id="bad-log-level"),
    ],
)
def test_validate_config_rejects_bad_settings(config: AppConfig, mutation: object) -> None:
    broken = mutation(config)  # type: ignore[operator]

    with pytest.raises(ConfigurationError):
        validate_config(broken)


def test_minimum_value_boundary_zero_is_valid(config: AppConfig) -> None:
    validate_config(replace(config, processing=replace(config.processing, minimum_value=0.0)))


@pytest.mark.parametrize(
    "line",
    [
        "  allowed_statuses: []\n",
        "  allowed_statuses: [1, 2]\n",
        "  allowed_statuses: in_use\n",
    ],
)
def test_malformed_allowed_statuses(config_path: Path, line: str) -> None:
    config_path.write_text(BASE_YAML + line, encoding="utf-8")

    with pytest.raises(ConfigurationError):
        load_and_validate(config_path)


# ------------------------------------------------------------- YAML / files
def test_missing_file_is_a_configuration_error_with_cause(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="not found") as exc_info:
        load_config(tmp_path / "nope.yaml")

    assert isinstance(exc_info.value.__cause__, FileNotFoundError)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("input: [unclosed", "Invalid YAML"),
        ("- a\n- b\n", "mapping"),
        ("output:\n  path: x\n", "section"),
        (BASE_YAML.replace("skip_invalid: true", "skip_invalid: 1"), "bool"),
        (BASE_YAML.replace("minimum_value: 0", "minimum_value: cheap"), "number"),
    ],
)
def test_malformed_yaml_documents(tmp_path: Path, text: str, message: str) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ConfigurationError, match=message):
        load_config(path)


def test_missing_input_file_fails_fast(config_path: Path) -> None:
    (config_path.parent / "input.csv").unlink()

    with pytest.raises(ConfigurationError, match="does not exist"):
        load_and_validate(config_path)


def test_output_directory_blocked_by_a_file(config_path: Path) -> None:
    (config_path.parent / "out").write_text("i am a file", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="cannot be created"):
        load_and_validate(config_path)


def test_shipped_configuration_is_valid() -> None:
    project = Path(__file__).resolve().parents[2]

    config = load_and_validate(project / "config.yaml", environ={})

    assert "decommissioned" in config.processing.allowed_statuses
    assert config.processing.skip_invalid is True
