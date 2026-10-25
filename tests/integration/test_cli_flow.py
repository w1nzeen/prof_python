"""Smoke tests of the command line interface of the whole project."""

import sys
from pathlib import Path

import pytest

from equipment_manager.main import main

pytestmark = pytest.mark.integration

PROJECT = Path(__file__).resolve().parents[2]


def run_cli(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], *args: str
) -> str:
    monkeypatch.setattr(sys, "argv", ["equipment-manager", *args])
    main()

    return capsys.readouterr().out


@pytest.mark.parametrize(
    ("flags", "expected"),
    [
        (["--demo"], "Most expensive device"),
        (["--analysis"], "Unique manufacturers"),
        (["--benchmark"], "dict search"),
        (["--oop"], "Registry as a collection"),
        (["--oop-experiments"], "Experiment 1: dependency injection"),
        (["--stream", "--path", str(PROJECT / "data" / "input.csv")], "Streaming pipeline"),
        (["--stream", "--path", str(PROJECT / "data" / "input.csv"), "-v"], "valid ="),
    ],
    ids=["demo", "analysis", "benchmark", "oop", "oop-experiments", "stream", "stream-verbose"],
)
def test_command_line_modes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    flags: list[str],
    expected: str,
) -> None:
    assert expected in run_cli(monkeypatch, capsys, *flags)


def test_generate_creates_the_file_in_the_current_directory(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    out = run_cli(monkeypatch, capsys, "--generate", "50")

    assert "Created data" in out
    assert len((tmp_path / "data" / "large.csv").read_text(encoding="utf-8").splitlines()) == 51


def test_interactive_menu_is_the_default_mode(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = iter(["6"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    assert "Goodbye." in run_cli(monkeypatch, capsys)


def test_unknown_flag_is_rejected(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        run_cli(monkeypatch, capsys, "--nonsense")

    assert exc_info.value.code == 2
