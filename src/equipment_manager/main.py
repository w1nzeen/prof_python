"""Application entry point: demo mode and console menu."""

import argparse

from equipment_manager import analytics, processors
from equipment_manager.benchmark import print_benchmark, run_benchmark
from equipment_manager.data import DEVICES
from equipment_manager.decorators import OPERATION_HISTORY
from equipment_manager.exceptions import EquipmentError
from equipment_manager.models import Device
from equipment_manager.services import (
    add_device,
    calculate_average_cost,
    calculate_total_cost,
    filter_by_manufacturer,
    find_device,
    find_most_expensive,
    search_devices,
)


def create_demo_devices() -> list[Device]:
    return [
        Device("PC-001", "Laptop", "Lenovo", "ThinkPad E14", 28500.00),
        Device("PC-002", "Laptop", "Dell", "Latitude 5440", 36900.00),
        Device("PC-003", "Monitor", "Dell", "U2723QE", 17200.50),
        Device("PC-004", "Printer", "HP", "LaserJet M111w", 4800.00),
        Device("PC-005", "Laptop", "Lenovo", "IdeaPad 3", 21300.00),
        Device("PC-006", "Router", "TP-Link", "Archer AX55", 3100.00),
    ]


def print_devices(devices: list[Device]) -> None:
    if not devices:
        print("No devices found.")
        return

    print(
        f"{'Inv.No':<9}{'Type':<10}{'Manufacturer':<14}"
        f"{'Model':<18}{'Cost':>11}"
    )

    for device in devices:
        print(
            f"{device.inventory_number:<9}"
            f"{device.device_type:<10}"
            f"{device.manufacturer:<14}"
            f"{device.model:<18}"
            f"{device.cost:>11.2f}"
        )


def print_statistics(devices: list[Device]) -> None:
    average = calculate_average_cost(devices)
    total = calculate_total_cost(devices)
    expensive = find_most_expensive(devices)

    print(f"Devices count: {len(devices)}")
    print(f"Average cost: {average:.2f}")
    print(f"Total cost: {total:.2f}")

    if expensive is not None:
        print(
            "Most expensive device:",
            f"{expensive.full_name} ({expensive.cost:.2f})",
        )


def read_cost(prompt: str) -> float:
    """Ask for a non-negative number until the input is valid."""
    while True:
        raw_value = input(prompt).strip().replace(",", ".")

        try:
            value = float(raw_value)
        except ValueError:
            print("Please enter a number.")
            continue

        if value < 0:
            print("Cost must not be negative.")
            continue

        return value


def read_device() -> Device:
    """Read device data from the keyboard."""
    return Device(
        inventory_number=input("Inventory number: ").strip(),
        device_type=input("Type: ").strip(),
        manufacturer=input("Manufacturer: ").strip(),
        model=input("Model: ").strip(),
        cost=read_cost("Cost: "),
    )


def print_menu() -> None:
    print()
    print("1. Show all devices")
    print("2. Search devices")
    print("3. Filter by manufacturer")
    print("4. Add device")
    print("5. Show statistics")
    print("6. Exit")


def run_menu(devices: list[Device]) -> None:
    while True:
        print_menu()
        command = input("Select command: ").strip()

        if command == "1":
            print_devices(devices)

        elif command == "2":
            query = input("Search query: ")
            print_devices(search_devices(devices, query))

        elif command == "3":
            manufacturer = input("Manufacturer: ")
            print_devices(filter_by_manufacturer(devices, manufacturer))

        elif command == "4":
            try:
                add_device(devices, read_device())
                print("Device added.")
            except EquipmentError as error:
                print(f"Error: {error}")

        elif command == "5":
            print_statistics(devices)

        elif command == "6":
            print("Goodbye.")
            break

        else:
            print("Unknown command.")


def run_demo(devices: list[Device]) -> None:
    print("Devices:")
    print_devices(devices)

    manufacturer = "Lenovo"
    result = filter_by_manufacturer(devices, manufacturer)
    print(f"\nDevices of manufacturer {manufacturer}:")
    print_devices(result)

    found = find_device(devices, "PC-003")

    if found is not None:
        print("\nDevice found:", found.full_name, found.device_type)

    print("\nSearch 'laptop':")
    print_devices(search_devices(devices, "laptop"))

    print("\nStatistics:")
    print_statistics(devices)


def print_section(title: str, devices: list[Device]) -> None:
    print(f"\n{title}")
    print("-" * 60)
    print_devices(devices)


def run_analysis(devices: list[Device]) -> None:
    """Laboratory work 2: structured data processing."""
    print_section("All devices", devices)

    manufacturers = processors.get_unique_manufacturers(devices)
    print("\nUnique manufacturers:", sorted(manufacturers))

    grouped = processors.group_by_manufacturer(devices)
    print("\nGrouped by manufacturer:")
    for manufacturer, items in grouped.items():
        print(f"  {manufacturer:<10} -> {len(items)} device(s)")

    nested = processors.group_by_type_and_manufacturer(devices)
    print("\nNested grouping (type -> manufacturer):")
    for device_type, by_manufacturer in nested.items():
        print(f"  {device_type}: {sorted(by_manufacturer)}")

    print("\nDevice types (Counter):")
    for device_type, count in processors.count_by_type(devices).most_common():
        print(f"  {device_type:<10} {count}")

    average = analytics.calculate_average_cost(devices)
    print(f"\nAverage cost: {average:.2f}")
    print(f"Total cost: {analytics.calculate_total_cost(devices):.2f}")

    minimum, maximum = analytics.calculate_cost_range(devices)
    print(f"Cost range: {minimum:.2f} - {maximum:.2f}")

    expensive = analytics.find_most_expensive(devices)
    if expensive is not None:
        print(
            "Most expensive device:",
            f"{expensive.full_name} ({expensive.cost:.2f})",
        )

    print("\nTotal cost by manufacturer:")
    totals = analytics.calculate_cost_by_manufacturer(devices)
    for manufacturer, total in sorted(totals.items()):
        print(f"  {manufacturer:<10} {total:>10.2f}")

    index = processors.create_device_index(devices)
    print("\nSearch by inventory number PC-008:")
    print(" ", processors.find_by_inventory_number(index, "PC-008"))

    lenovo = processors.filter_by_manufacturer(devices, "Lenovo")
    print_section("Manufacturer = Lenovo", lenovo)

    is_mid_price = analytics.create_cost_filter(10000, 30000)
    mid_price = processors.filter_items(devices, is_mid_price)
    print_section("Cost 10000..30000 (closure filter)", mid_price)

    ranking = analytics.sort_by_cost(devices)[:5]
    print_section("Top 5 by cost (sorted)", ranking)

    hp_laptops = processors.process_pipeline(
        devices,
        lambda items: processors.filter_items(
            items, analytics.create_manufacturer_filter("HP")
        ),
        lambda items: analytics.sort_by_cost(items, reverse=False),
    )
    print_section("Pipeline: HP devices sorted by cost", hp_laptops)

    average_values = analytics.calculate_average_values(100, 200, 300)
    print("\nAverage via *args:", average_values)

    new_device = analytics.create_device(
        inventory_number="PC-100",
        device_type="Mouse",
        manufacturer="Logitech",
        model="M90",
        cost=350.0,
    )
    print("Created via **kwargs:", new_device)

    print("\nLast operations (deque):", list(OPERATION_HISTORY))


def run_benchmark_report() -> None:
    print("Benchmark: search by inventory number (worst case)")
    print_benchmark(run_benchmark())


def main() -> None:
    parser = argparse.ArgumentParser(prog="equipment-manager")
    parser.add_argument(
        "--demo", action="store_true", help="laboratory work 1 demo"
    )
    parser.add_argument(
        "--analysis", action="store_true", help="laboratory work 2 demo"
    )
    parser.add_argument(
        "--benchmark", action="store_true", help="list vs dict benchmark"
    )
    args = parser.parse_args()

    if args.analysis:
        run_analysis(list(DEVICES))
    elif args.benchmark:
        run_benchmark_report()
    elif args.demo:
        run_demo(create_demo_devices())
    else:
        run_menu(create_demo_devices())


if __name__ == "__main__":
    main()
