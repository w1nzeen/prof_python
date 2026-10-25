"""The `--db` mode of the command line application."""

import sys
from pathlib import Path

import pytest

from equipment_manager.main import main

pytestmark = pytest.mark.integration


def run_database_demo(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    database: Path,
) -> str:
    monkeypatch.setattr(
        sys, "argv", ["equipment-manager", "--db", "--db-path", str(database)]
    )
    main()

    return capsys.readouterr().out


def test_database_demo_shows_every_part_of_the_lab(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    out = run_database_demo(monkeypatch, capsys, tmp_path / "nested" / "demo.db")

    assert "Registered 12 devices in one transaction" in out
    assert "Most expensive: HP ProLiant DL20" in out
    assert "DB-API (sqlite3, parameterized query)" in out
    assert "Room 101" in out
    assert "-> ROLLBACK" in out
    assert "Devices before/after: 11/11" in out
    assert "Manufacturer Acer was not stored: True" in out


def test_database_demo_can_be_repeated_on_the_same_file(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    database = tmp_path / "demo.db"

    first = run_database_demo(monkeypatch, capsys, database)
    second = run_database_demo(monkeypatch, capsys, database)

    assert first == second.replace("\r", "")
