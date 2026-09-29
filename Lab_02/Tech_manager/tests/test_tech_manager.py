from tech_manager.analytics import (
    calculate_average_values,
    calculate_total_price,
    find_most_expensive,
    get_price_range,
)
from tech_manager.data import create_demo_tech_list, generate_tech_list
from tech_manager.processors import (
    count_by_type,
    create_inventory_index,
    create_price_filter,
    create_tech,
    filter_by_vendor,
    filter_items,
    find_by_inventory_number,
    find_linear,
    get_unique_vendors,
    group_by_vendor,
    group_by_vendor_and_type,
    pipeline,
    search_tech,
    sort_by_price,
)


def test_unique_vendors():
    assert get_unique_vendors(create_demo_tech_list()) == {
        "Dell", "Apple", "Samsung", "HP", "Google", "Lenovo",
    }


def test_index_and_search():
    tech_list = create_demo_tech_list()
    index = create_inventory_index(tech_list)
    assert find_by_inventory_number(index, "005").model == "Pixel 6"
    assert find_by_inventory_number(index, "999") is None
    assert find_linear(tech_list, "005") == index["005"]


def test_group_and_counter():
    tech_list = create_demo_tech_list()
    assert len(group_by_vendor(tech_list)["Dell"]) == 3
    assert count_by_type(tech_list)["Laptop"] == 4
    assert "Laptop" in group_by_vendor_and_type(tech_list)["Dell"]


def test_filters_and_search():
    tech_list = create_demo_tech_list()
    assert len(filter_by_vendor(tech_list, "dell", "HP")) == 5
    assert all(600 <= t.price <= 1000
               for t in filter_items(tech_list, create_price_filter(600, 1000)))
    assert len(search_tech(tech_list, vendor="DELL", type="laptop")) == 2


def test_aggregation():
    tech_list = create_demo_tech_list()
    assert calculate_average_values() == 0.0
    assert calculate_average_values(10, 20, 30) == 20
    assert round(calculate_total_price(tech_list), 2) == 10104.35
    assert find_most_expensive(tech_list).inventory_number == "008"
    assert find_most_expensive([]) is None
    assert get_price_range(tech_list) == (189.9, 1899.0)


def test_sort_pipeline_and_create():
    tech_list = create_demo_tech_list()
    assert sort_by_price(tech_list)[0].inventory_number == "008"
    result = pipeline(tech_list, lambda items: items[:3], sort_by_price)
    assert [t.inventory_number for t in result] == ["001", "002", "003"]
    tech = create_tech(inventory_number="1", type="Laptop", vendor="A", model="B", price="10")
    assert tech.price == 10.0 and tech.vendor_model == ("A", "B")


def test_generate_unique_numbers():
    items = generate_tech_list(500)
    assert len({t.inventory_number for t in items}) == 500
