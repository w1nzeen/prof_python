from collections import Counter

from equipment_manager import processors
from equipment_manager.data import DEVICES, generate_devices


def test_unique_and_index() -> None:
    assert processors.get_unique_manufacturers(DEVICES) == {
        "Lenovo", "Dell", "HP", "Asus", "TP-Link",
    }
    index = processors.create_device_index(DEVICES)
    assert len(index) == len(DEVICES)
    assert index["PC-008"].model == "ProLiant DL20"
    assert processors.find_by_inventory_number(index, "none") is None


def test_grouping() -> None:
    grouped = processors.group_by_manufacturer(DEVICES)
    assert sum(len(items) for items in grouped.values()) == len(DEVICES)
    nested = processors.group_by_type_and_manufacturer(DEVICES)
    assert "Dell" in nested["Laptop"]


def test_counter() -> None:
    counter = processors.count_by_type(DEVICES)
    assert isinstance(counter, Counter)
    assert counter["Laptop"] == 4


def test_filter_and_pipeline() -> None:
    result = processors.filter_by_manufacturer(DEVICES, " hp ")
    assert {d.manufacturer for d in result} == {"HP"}
    piped = processors.process_pipeline(
        DEVICES,
        lambda items: processors.filter_items(
            items, lambda d: d.device_type == "Monitor"
        ),
    )
    assert len(piped) == 3


def test_linear_and_index_agree() -> None:
    devices = generate_devices(500)
    index = processors.create_device_index(devices)
    target = devices[-1].inventory_number
    assert processors.find_linear(devices, target) is index[target]
