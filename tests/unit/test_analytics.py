import pytest

from equipment_manager import analytics
from equipment_manager.data import DEVICES
from equipment_manager.decorators import OPERATION_HISTORY, record_operation
from equipment_manager.exceptions import InvalidDeviceError


def test_aggregations(capsys: pytest.CaptureFixture[str]) -> None:
    total = analytics.calculate_total_cost(DEVICES)
    assert analytics.calculate_average_cost(DEVICES) == pytest.approx(
        total / len(DEVICES)
    )
    assert "calculate_average_cost" in capsys.readouterr().out
    assert analytics.calculate_cost_range(DEVICES) == (450.0, 74500.0)
    assert analytics.calculate_cost_range([]) == (0.0, 0.0)


def test_most_expensive_and_sort() -> None:
    best = analytics.find_most_expensive(DEVICES)
    assert best is not None and best.inventory_number == "PC-008"
    costs = [d.cost for d in analytics.sort_by_cost(DEVICES)]
    assert costs == sorted(costs, reverse=True)


def test_cost_by_manufacturer() -> None:
    totals = analytics.calculate_cost_by_manufacturer(DEVICES)
    assert sum(totals.values()) == pytest.approx(
        analytics.calculate_total_cost(DEVICES)
    )


def test_args_kwargs() -> None:
    assert analytics.calculate_average_values(10, 20, 30) == 20
    assert analytics.calculate_average_values() == 0.0
    device = analytics.create_device(
        inventory_number="X-1",
        device_type="Mouse",
        manufacturer="Logitech",
        model="M90",
        cost=10.0,
    )
    assert device.full_name == "Logitech M90"
    with pytest.raises(InvalidDeviceError):
        analytics.create_device(
            inventory_number="X-2", device_type="Mouse",
            manufacturer="Logitech", model="M90", cost=-1.0,
        )


def test_closure_filters() -> None:
    in_range = analytics.create_cost_filter(10000, 30000)
    assert [d.inventory_number for d in DEVICES if in_range(d)] == [
        "PC-001", "PC-003", "PC-005", "PC-007", "PC-010",
    ]
    at_least = analytics.create_cost_filter(70000)
    assert [d.inventory_number for d in DEVICES if at_least(d)] == ["PC-008"]


def test_history_deque() -> None:
    OPERATION_HISTORY.clear()
    for _ in range(8):
        analytics.find_most_expensive(DEVICES)
    assert len(OPERATION_HISTORY) == OPERATION_HISTORY.maxlen == 5


def test_decorator_keeps_name() -> None:
    @record_operation(OPERATION_HISTORY)
    def sample() -> int:
        """Doc."""
        return 1

    assert sample.__name__ == "sample" and sample.__doc__ == "Doc."
