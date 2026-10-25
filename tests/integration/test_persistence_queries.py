"""Search, filters and SQL aggregates (JOIN, GROUP BY, SUM, AVG, LIMIT)."""

import pytest

from equipment_manager.data import DEVICES
from equipment_manager.models import Device
from equipment_manager.persistence.services import EquipmentService
from equipment_manager.services import (
    calculate_average_cost,
    calculate_total_cost,
    filter_by_manufacturer,
    find_most_expensive,
    search_devices,
)

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "query",
    ["pc-00", "LAPTOP", "thinkpad", "lenovo", "  Lenovo  "],
    ids=["number", "type", "model", "manufacturer", "spaces"],
)
def test_search_matches_every_searchable_field_ignoring_case(
    seeded: EquipmentService, query: str
) -> None:
    assert seeded.search_devices(query)


def test_search_result_equals_the_in_memory_search_of_lab_1(
    seeded: EquipmentService,
) -> None:
    for query in ("laptop", "dell", "pc-01", "pro", "nothing"):
        database = [d.inventory_number for d in seeded.search_devices(query)]
        memory = sorted(d.inventory_number for d in search_devices(DEVICES, query))

        assert database == memory


def test_search_treats_like_wildcards_literally(seeded: EquipmentService) -> None:
    assert seeded.search_devices("%") == []
    assert seeded.search_devices("_") == []


def test_filter_by_manufacturer_ignores_case(seeded: EquipmentService) -> None:
    result = seeded.filter_by_manufacturer("dELL")

    assert [d.inventory_number for d in result] == ["PC-002", "PC-003", "PC-012"]


def test_filter_by_unknown_manufacturer_is_empty(seeded: EquipmentService) -> None:
    assert seeded.filter_by_manufacturer("Apple") == []


def test_filter_equals_lab_1_filter(seeded: EquipmentService) -> None:
    database = {d.inventory_number for d in seeded.filter_by_manufacturer("HP")}
    memory = {d.inventory_number for d in filter_by_manufacturer(DEVICES, "HP")}

    assert database == memory


def test_sql_aggregates_equal_lab_1_functions(seeded: EquipmentService) -> None:
    stats = seeded.statistics()

    assert stats.count == len(DEVICES)
    assert stats.total_cost == pytest.approx(calculate_total_cost(DEVICES))
    assert stats.average_cost == pytest.approx(calculate_average_cost(DEVICES))

    expected = find_most_expensive(DEVICES)
    assert expected is not None
    assert stats.most_expensive is not None
    assert stats.most_expensive.inventory_number == expected.inventory_number


def test_group_by_counts_and_totals(seeded: EquipmentService) -> None:
    assert seeded.devices.count_by_manufacturer() == {
        "Asus": 2,
        "Dell": 3,
        "HP": 3,
        "Lenovo": 3,
        "TP-Link": 1,
    }

    totals = seeded.devices.total_cost_by_manufacturer()

    assert totals["HP"] == pytest.approx(4800 + 74500 + 8700)
    assert totals["TP-Link"] == pytest.approx(3100)
    assert sum(totals.values()) == pytest.approx(seeded.statistics().total_cost)


def test_aggregates_of_an_empty_database(service: EquipmentService) -> None:
    stats = service.statistics()

    assert stats.count == 0
    assert stats.total_cost == 0.0
    assert stats.average_cost == 0.0
    assert stats.most_expensive is None
    assert stats.count_by_manufacturer == {}


def test_most_expensive_prefers_the_first_device_on_a_tie(
    service: EquipmentService,
) -> None:
    service.register_device(Device("PC-1", "Laptop", "Acer", "A", 100.0))
    service.register_device(Device("PC-2", "Laptop", "Acer", "B", 100.0))

    winner = service.statistics().most_expensive

    assert winner is not None
    assert winner.inventory_number == "PC-1"


def test_aggregates_see_updates_made_by_the_service(
    seeded: EquipmentService,
) -> None:
    seeded.change_cost("PC-006", 103100.0)

    stats = seeded.statistics()

    assert stats.most_expensive is not None
    assert stats.most_expensive.inventory_number == "PC-006"
    assert stats.total_cost == pytest.approx(calculate_total_cost(DEVICES) + 100000)


def test_row_converts_back_to_the_dataclass_of_lab_1(
    seeded: EquipmentService,
) -> None:
    row = seeded.get_device("PC-004")

    assert row.to_device() == DEVICES[3]
