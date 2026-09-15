from tech_manager.decorators import repeat
from tech_manager.models import TECH_TYPES, Tech
from tech_manager.services import (
    average_of_values,
    avg_price,
    benchmark_search,
    build_summary_report,
    count_by_type,
    count_by_vendor,
    create_price_filter,
    create_tech_index,
    create_tech_record,
    filter_by_price_range,
    filter_items,
    find_cheapest_tech,
    find_most_expensive_tech,
    get_search_history,
    get_unique_types,
    get_unique_vendors,
    group_by_type,
    group_by_vendor_and_type,
    price_of_all_tech,
    process_pipeline,
    search_by_model,
    sort_by_vendor,
    sort_items,
)


def create_demo_tech_list() -> list[Tech]:
    return [
        Tech(inventory_number="001", type="Laptop", vendor="Dell", model="XPS 13", price=999.99),
        Tech(inventory_number="002", type="Smartphone", vendor="Apple", model="iPhone 13", price=799.99),
        Tech(inventory_number="003", type="Tablet", vendor="Samsung", model="Galaxy Tab S7", price=649.99),
        Tech(inventory_number="004", type="Laptop", vendor="HP", model="Spectre x360", price=1199.99),
        Tech(inventory_number="005", type="Smartphone", vendor="Google", model="Pixel 6", price=599.99),
        Tech(inventory_number="006", type="Monitor", vendor="Dell", model="UltraSharp U2720Q", price=549.99),
        Tech(inventory_number="007", type="Laptop", vendor="Apple", model="MacBook Air M2", price=1099.00),
        Tech(inventory_number="008", type="Printer", vendor="HP", model="LaserJet Pro", price=249.99),
    ]


def print_tech_list(tech_list: list[Tech]) -> None:
    for tech in tech_list:
        print(
            f"Inventory Number: {tech.inventory_number}, Type: {tech.type}, "
            f"Vendor: {tech.vendor}, Model: {tech.model}, Price: ${tech.price:.2f}"
        )


def print_menu() -> None:
    print("\nTech Manager Menu:")
    print(" 1. View all tech items")
    print(" 2. Search by model")
    print(" 3. Sort by vendor")
    print(" 4. Sort by price (universal sort)")
    print(" 5. Calculate average price")
    print(" 6. Find the most expensive / cheapest tech item")
    print(" 7. Filter by price range")
    print(" 8. Filter by price using a closure (price >= threshold)")
    print(" 9. Unique vendors and unique types")
    print("10. Group by type / group by vendor and type (nested)")
    print("11. Count items by type and by vendor (Counter)")
    print("12. Build tech index and search by inventory number")
    print("13. Total price of all tech items / summary report")
    print("14. Benchmark: list search vs dict search")
    print("15. Demo: *args, **kwargs, pipeline, decorators, search history")
    print("16. Exit")


def run_args_kwargs_pipeline_demo(tech_list: list[Tech]) -> None:
    demo_average = average_of_values(999.99, 799.99, 649.99, 1199.99)
    print(f"\nAverage via *args: ${demo_average:.2f}")

    new_tech = create_tech_record(
        inventory_number="009",
        type="Tablet",
        vendor="Lenovo",
        model="Tab P11",
        price=349.99,
    )
    print(f"Created via **kwargs: {new_tech}")

    cheap_laptops = process_pipeline(
        tech_list,
        lambda items: filter_items(items, create_price_filter(0)),
        lambda items: [tech for tech in items if tech.type == "Laptop"],
        lambda items: sort_items(items, key=lambda tech: tech.price),
    )
    print("\nPipeline result (laptops sorted by price):")
    print_tech_list(cheap_laptops)

    @repeat(3)
    def show_message() -> None:
        print("Processing...")

    print("\nParameterized decorator demo (@repeat(3)):")
    show_message()

    print("\nAllowed tech types (tuple):", TECH_TYPES)
    print("Recent search history (deque snapshot):", get_search_history())


def main() -> None:
    tech_list = create_demo_tech_list()

    choice = 0

    while choice != 16:

        print_menu()
        choice = int(input("Enter your choice: "))

        if choice == 1:
            print("\nAll Tech Items:")
            print_tech_list(tech_list)
        elif choice == 2:
            model = input("Enter the model to search for: ")
            search_results = search_by_model(tech_list, model)
            print("\nSearch Results:")
            print_tech_list(search_results)
        elif choice == 3:
            sorted_tech = sort_by_vendor(tech_list)
            print("\nSorted by Vendor:")
            print_tech_list(sorted_tech)
        elif choice == 4:
            sorted_tech = sort_items(tech_list, key=lambda tech: tech.price)
            print("\nSorted by Price:")
            print_tech_list(sorted_tech)
        elif choice == 5:
            average_price = avg_price(tech_list)
            print(f"\nAverage Price of Tech Items: ${average_price:.2f}")
        elif choice == 6:
            most_expensive = find_most_expensive_tech(tech_list)
            cheapest = find_cheapest_tech(tech_list)
            if most_expensive:
                print(f"\nMost Expensive: {most_expensive.name} - ${most_expensive.price:.2f}")
            if cheapest:
                print(f"Cheapest: {cheapest.name} - ${cheapest.price:.2f}")
        elif choice == 7:
            min_price = float(input("Enter minimum price: "))
            max_price = float(input("Enter maximum price: "))
            filtered_tech = filter_by_price_range(tech_list, min_price, max_price)
            print("\nFiltered by Price Range:")
            print_tech_list(filtered_tech)
        elif choice == 8:
            threshold = float(input("Enter minimum price threshold: "))
            is_above_threshold = create_price_filter(threshold)
            filtered_tech = filter_items(tech_list, is_above_threshold)
            print(f"\nItems with price >= ${threshold:.2f}:")
            print_tech_list(filtered_tech)
        elif choice == 9:
            print("\nUnique vendors:", get_unique_vendors(tech_list))
            print("Unique types:", get_unique_types(tech_list))
        elif choice == 10:
            grouped = group_by_type(tech_list)
            print("\nGrouped by type:")
            for tech_type, items in grouped.items():
                print(f"  {tech_type} -> {len(items)} item(s)")
            nested = group_by_vendor_and_type(tech_list)
            print("\nGrouped by vendor and type (nested):")
            for vendor, types_dict in nested.items():
                print(f"  {vendor}:")
                for tech_type, items in types_dict.items():
                    print(f"    {tech_type} -> {len(items)} item(s)")
        elif choice == 11:
            print("\nCount by type:", count_by_type(tech_list))
            print("Count by vendor:", count_by_vendor(tech_list))
        elif choice == 12:
            index = create_tech_index(tech_list)
            inventory_number = input("Enter inventory number to look up: ")
            found = index.get(inventory_number)
            print("\nSearch by inventory number:", found if found else "Not found")
        elif choice == 13:
            total_price = price_of_all_tech(tech_list)
            print(f"\nTotal Price of All Tech Items: ${total_price:.2f}")
            print("Summary report:", build_summary_report(tech_list))
        elif choice == 14:
            inventory_number = input("Enter inventory number to benchmark search for: ")
            timings = benchmark_search(tech_list, inventory_number)
            print(f"\nList search: {timings['list_search_seconds']:.8f} s")
            print(f"Dict search: {timings['dict_search_seconds']:.8f} s")
        elif choice == 15:
            run_args_kwargs_pipeline_demo(tech_list)
        elif choice == 16:
            print("Exiting the program.")
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()