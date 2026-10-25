"""Console menu and helpers of laboratory work 1 (input monkeypatched)."""

from collections.abc import Iterator

import pytest

from equipment_manager.main import (
    create_demo_devices,
    print_devices,
    print_statistics,
    read_cost,
    read_device,
    run_demo,
    run_menu,
)
from equipment_manager.models import Device as SimpleDevice


def feed(monkeypatch: pytest.MonkeyPatch, answers: list[str]) -> None:
    iterator: Iterator[str] = iter(answers)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(iterator))


def test_read_cost_repeats_until_valid(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    feed(monkeypatch, ["abc", "-5", "350,5"])

    assert read_cost("Cost: ") == pytest.approx(350.5)

    out = capsys.readouterr().out
    assert "Please enter a number." in out
    assert "must not be negative" in out


def test_read_device_builds_a_device(monkeypatch: pytest.MonkeyPatch) -> None:
    feed(monkeypatch, ["PC-050", "Mouse", "Logitech", "M90", "199"])

    device = read_device()

    assert isinstance(device, SimpleDevice)
    assert (device.inventory_number, device.cost) == ("PC-050", 199.0)


def test_menu_flow_add_search_statistics_exit(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    feed(
        monkeypatch,
        [
            "1",
            "2", "laptop",
            "3", "dell",
            "4", "PC-100", "Mouse", "Logitech", "M90", "300",
            "4", "PC-100", "Mouse", "Logitech", "M90", "300",
            "5",
            "9",
            "6",
        ],
    )
    devices = create_demo_devices()

    run_menu(devices)

    out = capsys.readouterr().out
    assert "Device added." in out
    assert "Error:" in out  # the duplicate inventory number
    assert "Unknown command." in out
    assert "Goodbye." in out
    assert len(devices) == 7


def test_print_devices_for_empty_list(capsys: pytest.CaptureFixture[str]) -> None:
    print_devices([])

    assert capsys.readouterr().out.strip() == "No devices found."


def test_statistics_output(capsys: pytest.CaptureFixture[str]) -> None:
    print_statistics(create_demo_devices())

    out = capsys.readouterr().out
    assert "Devices count: 6" in out
    assert "Total cost: 111800.50" in out
    assert "Most expensive device: Dell Latitude 5440" in out


def test_statistics_of_empty_list(capsys: pytest.CaptureFixture[str]) -> None:
    print_statistics([])

    out = capsys.readouterr().out
    assert "Devices count: 0" in out
    assert "Most expensive" not in out


def test_demo_runs(capsys: pytest.CaptureFixture[str]) -> None:
    run_demo(create_demo_devices())

    assert "Statistics:" in capsys.readouterr().out
