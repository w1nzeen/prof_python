"""MaintenanceService and ReportService tested with test doubles."""

import logging
from collections.abc import Callable
from datetime import date
from unittest.mock import Mock, create_autospec

import pytest

from equipment_manager.domain.dto import InventoryReport
from equipment_manager.domain.exceptions import MaintenanceError
from equipment_manager.domain.models import (
    Computer,
    Device,
    DeviceStatus,
    InventoryRegistry,
    Printer,
)
from equipment_manager.domain.policies import FixedIntervalPolicy, MaintenancePolicy
from equipment_manager.domain.protocols import ReportFormatter
from equipment_manager.domain.services import MaintenanceService, ReportService

DeviceFactory = Callable[..., Device]


@pytest.fixture
def policy_mock() -> Mock:
    mock: Mock = create_autospec(MaintenancePolicy, instance=True)
    return mock


@pytest.fixture
def service(
    populated_registry: InventoryRegistry, notifier: Mock
) -> MaintenanceService:
    return MaintenanceService(
        populated_registry, FixedIntervalPolicy(180), notifier, "ops@example.com"
    )


# --------------------------------------------------------- return_value
def test_due_devices_follow_the_policy_answer(
    populated_registry: InventoryRegistry,
    policy_mock: Mock,
    notifier: Mock,
    today: date,
) -> None:
    policy_mock.is_due.return_value = True
    service = MaintenanceService(populated_registry, policy_mock, notifier)

    assert len(service.due_devices(today)) == 3
    assert policy_mock.is_due.call_count == 3

    policy_mock.is_due.return_value = False

    assert service.due_devices(today) == []


def test_not_due_devices_are_not_notified(
    populated_registry: InventoryRegistry,
    policy_mock: Mock,
    notifier: Mock,
    today: date,
) -> None:
    policy_mock.is_due.return_value = False
    service = MaintenanceService(populated_registry, policy_mock, notifier)

    assert service.notify_due(today) == 0

    notifier.send.assert_not_called()


def test_notification_text_uses_policy_due_date(
    populated_registry: InventoryRegistry,
    policy_mock: Mock,
    notifier: Mock,
    today: date,
    computer: Computer,
) -> None:
    policy_mock.is_due.side_effect = lambda device, _day: device is computer
    policy_mock.next_due.return_value = date(2026, 1, 2)
    service = MaintenanceService(populated_registry, policy_mock, notifier, "ops@x.io")

    assert service.notify_due(today) == 1

    notifier.send.assert_called_once_with(
        "ops@x.io",
        f"Maintenance due since 2026-01-02: {computer}",
    )


# ------------------------------------------------------ interaction tests
def test_notify_due_sends_one_message_per_due_device(
    service: MaintenanceService, notifier: Mock, today: date
) -> None:
    sent = service.notify_due(today)

    assert sent == 3
    assert notifier.send.call_count == 3
    recipients = {call.args[0] for call in notifier.send.call_args_list}
    assert recipients == {"ops@example.com"}


def test_perform_records_work_and_notifies_once(
    service: MaintenanceService,
    notifier: Mock,
    computer: Computer,
    today: date,
) -> None:
    record = service.perform("PC-001", "Cleaning", today, "I. Koval")

    assert computer.maintenance_history == (record,)
    assert record.technician == "I. Koval"
    notifier.send.assert_called_once_with(
        "ops@example.com", "Maintenance done for PC-001: Cleaning"
    )


def test_unknown_device_causes_no_notification(
    service: MaintenanceService, notifier: Mock, today: date
) -> None:
    from equipment_manager.domain.exceptions import DeviceNotFoundError

    with pytest.raises(DeviceNotFoundError):
        service.perform("PC-999", "Cleaning", today)

    notifier.send.assert_not_called()


def test_invalid_maintenance_date_causes_no_notification(
    service: MaintenanceService, notifier: Mock, computer: Computer
) -> None:
    with pytest.raises(MaintenanceError):
        service.perform("PC-001", "Too early", date(2000, 1, 1))

    assert computer.maintenance_history == ()
    notifier.send.assert_not_called()


# ---------------------------------------------------- status rules
def test_decommissioned_devices_are_never_due(
    service: MaintenanceService, notifier: Mock, printer: Printer, today: date
) -> None:
    printer.change_status(DeviceStatus.DECOMMISSIONED)

    due = service.due_devices(today)

    assert printer not in due
    assert service.notify_due(today) == len(due)


def test_maintenance_resets_the_due_date(
    service: MaintenanceService, computer: Computer, today: date
) -> None:
    assert computer in service.due_devices(today)

    service.perform("PC-001", "Cleaning", today)

    assert computer not in service.due_devices(today)


# ------------------------------------------------------- side_effect
def test_notifier_failure_does_not_hide_performed_maintenance(
    service: MaintenanceService,
    notifier: Mock,
    computer: Computer,
    today: date,
    caplog: pytest.LogCaptureFixture,
) -> None:
    notifier.send.side_effect = ConnectionError("SMTP is down")
    caplog.set_level(logging.WARNING)

    record = service.perform("PC-001", "Cleaning", today)

    assert computer.maintenance_history == (record,)
    notifier.send.assert_called_once()
    assert "SMTP is down" in caplog.text or "Notification failed" in caplog.text


def test_side_effect_can_return_different_values(
    populated_registry: InventoryRegistry,
    policy_mock: Mock,
    notifier: Mock,
    today: date,
) -> None:
    policy_mock.is_due.side_effect = [True, False, True]
    service = MaintenanceService(populated_registry, policy_mock, notifier)

    assert len(service.due_devices(today)) == 2


def test_autospec_rejects_wrong_signature(notifier: Mock) -> None:
    with pytest.raises(TypeError):
        notifier.send("only-one-argument")

    with pytest.raises(AttributeError):
        _ = notifier.broadcast  # not part of the Notifier protocol


# ----------------------------------------------------------- reports
def test_report_service_passes_report_to_formatter(
    populated_registry: InventoryRegistry,
) -> None:
    formatter = create_autospec(ReportFormatter, instance=True)
    formatter.format.return_value = "REPORT TEXT"
    service = ReportService(populated_registry, formatter)

    assert service.render() == "REPORT TEXT"

    formatter.format.assert_called_once()
    report = formatter.format.call_args.args[0]
    assert isinstance(report, InventoryReport)
    assert report.total_devices == 3


def test_build_report_content(populated_registry: InventoryRegistry) -> None:
    report = ReportService(populated_registry, Mock(spec=ReportFormatter)).build_report()

    assert report.total_devices == 3
    assert float(report.total_cost.amount) == pytest.approx(50500.50)
    assert report.most_expensive is not None
    assert report.most_expensive.startswith("PC-001")
    assert report.by_kind == {"Computer": 1, "Printer": 1, "Device": 1}


def test_report_of_empty_registry(registry: InventoryRegistry) -> None:
    report = ReportService(registry, Mock(spec=ReportFormatter)).build_report()

    assert report.total_devices == 0
    assert report.most_expensive is None
    assert report.by_manufacturer == {}


def test_formatter_failure_propagates(populated_registry: InventoryRegistry) -> None:
    formatter = create_autospec(ReportFormatter, instance=True)
    formatter.format.side_effect = RuntimeError("template broken")

    with pytest.raises(RuntimeError, match="template broken"):
        ReportService(populated_registry, formatter).render()


def test_notifier_protocol_mock_is_not_called_by_report(
    populated_registry: InventoryRegistry, notifier: Mock
) -> None:
    ReportService(populated_registry, Mock(spec=ReportFormatter)).build_report()

    notifier.send.assert_not_called()



