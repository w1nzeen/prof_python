from functools import partial

from tech_manager.analytics import (
    build_summary,
    calculate_average_price,
    calculate_total_price,
    export_summary,
    find_most_expensive,
    get_price_range,
    total_price_by_vendor,
)
from tech_manager.data import DEMO_PRICE_RANGE, create_demo_tech_list
from tech_manager.decorators import OPERATION_HISTORY
from tech_manager.models import Tech
from tech_manager.processors import (
    count_by_type,
    create_inventory_index,
    create_price_filter,
    create_tech,
    create_vendor_filter,
    filter_by_vendor,
    filter_items,
    find_by_inventory_number,
    get_unique_types,
    get_unique_vendors,
    group_by_type,
    group_by_vendor,
    group_by_vendor_and_type,
    pipeline,
    search_tech,
    sort_by_price,
    sort_items,
)


def print_tech_list(title: str, items: list[Tech]) -> None:
    print(f"\n{title}")
    print("-" * 70)
    for tech in items:
        print(
            f"{tech.inventory_number:4} "
            f"{tech.type:11} "
            f"{tech.vendor:9} "
            f"{tech.model:16} "
            f"{tech.price:9.2f}"
        )


def show_basic_info(tech_list: list[Tech]) -> None:
    print_tech_list("All devices", tech_list)
    print("\nUnique vendors:", sorted(get_unique_vendors(tech_list)))
    print("Unique types:  ", sorted(get_unique_types(tech_list)))
    print("Counter of types:", dict(count_by_type(tech_list)))


def show_aggregation(tech_list: list[Tech]) -> None:
    print()
    average = calculate_average_price(tech_list)
    print(f"Average price: {average:.2f}")
    print(f"Total price:   {calculate_total_price(tech_list):.2f}")
    minimum, maximum = get_price_range(tech_list)
    print(f"Price range:   {minimum:.2f} .. {maximum:.2f}")
    most_expensive = find_most_expensive(tech_list)
    if most_expensive:
        print(f"Most expensive: {most_expensive.name} ({most_expensive.price})")
    print("Total price by vendor:", total_price_by_vendor(tech_list))


def show_grouping(tech_list: list[Tech]) -> None:
    print("\nGrouped by vendor:")
    for vendor, items in group_by_vendor(tech_list).items():
        print(f"  {vendor:8} -> {len(items)}")
    print("Grouped by type:")
    for tech_type, items in group_by_type(tech_list).items():
        print(f"  {tech_type:10} -> {len(items)}")
    print("Nested grouping (vendor -> type):")
    for vendor, types in group_by_vendor_and_type(tech_list).items():
        print(f"  {vendor:8}", {t: len(v) for t, v in types.items()})


def show_search_and_filters(tech_list: list[Tech]) -> None:
    index = create_inventory_index(tech_list)
    print("\nSearch by inventory number '003':", find_by_inventory_number(index, "003"))
    print("Search by kwargs (vendor=dell, type=laptop):")
    for tech in search_tech(tech_list, vendor="dell", type="laptop"):
        print("  ", tech.name, tech.price)

    print_tech_list("Filter by vendor (Dell, HP)", filter_by_vendor(tech_list, "Dell", "HP"))

    low, high = DEMO_PRICE_RANGE
    in_range = filter_items(tech_list, create_price_filter(low, high))
    print_tech_list(f"Price in [{low}, {high}] (closure)", in_range)

    expensive = filter_items(tech_list, lambda tech: tech.price >= 1000)
    print_tech_list("Price >= 1000 (lambda)", expensive)


def show_sorting_and_pipeline(tech_list: list[Tech]) -> None:
    print_tech_list("Sorted by price (desc)", sort_by_price(tech_list))
    by_model = sort_items(tech_list, key=lambda tech: tech.model.lower())
    print_tech_list("Sorted by model (universal sort)", by_model[:4])

    result = pipeline(
        tech_list,
        partial(filter_items, predicate=create_vendor_filter("Dell", "HP", "Lenovo")),
        partial(filter_items, predicate=create_price_filter(500, 2000)),
        sort_by_price,
    )
    print_tech_list("Pipeline: vendor filter -> price filter -> sort", result)


def show_kwargs_and_history() -> None:
    new_tech = create_tech(
        inventory_number="013",
        type="Laptop",
        vendor="Asus",
        model="Zenbook 14",
        price="1099.5",
    )
    print("\nCreated via **kwargs:", new_tech)
    print("vendor_model tuple:", new_tech.vendor_model)
    print("Last operations (deque, maxlen=5):", list(OPERATION_HISTORY))


def main() -> None:
    tech_list = create_demo_tech_list()
    show_basic_info(tech_list)
    show_aggregation(tech_list)
    show_grouping(tech_list)
    show_search_and_filters(tech_list)
    show_sorting_and_pipeline(tech_list)
    show_kwargs_and_history()

    path = export_summary(build_summary(tech_list), "summary.json")
    print(f"\nSummary exported to {path}")


if __name__ == "__main__":
    main()
