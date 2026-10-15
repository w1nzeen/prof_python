"""Console demonstration of laboratory work 4."""

import contextlib
import io
from datetime import date

from equipment_manager.domain.adapters import (
    ConsoleNotifier,
    InMemoryNotifier,
    JsonReportFormatter,
)
from equipment_manager.domain.container import Container, build_container
from equipment_manager.domain.dto import (
    ComputerPayload,
    DevicePayload,
    GenericPayload,
    PrinterPayload,
    device_from_payload,
    device_to_payload,
)
from equipment_manager.domain.exceptions import DomainError
from equipment_manager.domain.experiments import (
    AlertServiceA,
    AlertServiceB,
    CostValidator,
    CsvProcessor,
    LabelFormatter,
    Processor,
    SeparatorParser,
    UpperFormatter,
    UpperSemicolonProcessor,
)
from equipment_manager.domain.models import (
    Computer,
    Device,
    Manufacturer,
    Printer,
    PrintTechnology,
)
from equipment_manager.domain.protocols import Serializable
from equipment_manager.domain.value_objects import InventoryNumber, Money

TODAY = date(2026, 10, 15)


def sample_devices() -> list[Device]:
    lenovo = Manufacturer("Lenovo", "China")
    hp = Manufacturer("HP", "USA")

    return [
        Computer(
            inventory_number=InventoryNumber("PC-001"),
            manufacturer=lenovo,
            model="ThinkPad E14",
            cost=Money.of(28500),
            purchased_on=date(2025, 1, 15),
            cpu="Intel Core i5-1335U",
            ram_gb=16,
            storage_gb=512,
        ),
        Computer(
            inventory_number=InventoryNumber("PC-005"),
            manufacturer=lenovo,
            model="IdeaPad 3",
            cost=Money.of(21300),
            purchased_on=date(2025, 6, 1),
            cpu="AMD Ryzen 5 5500U",
            ram_gb=8,
            storage_gb=512,
        ),
        Printer(
            inventory_number=InventoryNumber("PC-004"),
            manufacturer=hp,
            model="LaserJet M111w",
            cost=Money.of(4800),
            purchased_on=date(2024, 9, 20),
            technology=PrintTechnology.LASER,
            pages_per_minute=20,
        ),
    ]


def sample_payloads() -> list[DevicePayload]:
    computer: ComputerPayload = {
        "kind": "computer",
        "inventory_number": "PC-002",
        "manufacturer": "Dell",
        "country": "USA",
        "model": "Latitude 5440",
        "cost": 36900.0,
        "purchased_on": "2024-03-10",
        "cpu": "Intel Core i7-1355U",
        "ram_gb": 32,
        "storage_gb": 1024,
    }
    printer: PrinterPayload = {
        "kind": "printer",
        "inventory_number": "PC-009",
        "manufacturer": "HP",
        "country": "USA",
        "model": "OfficeJet Pro 9010",
        "cost": 8700.0,
        "purchased_on": "2026-02-05",
        "technology": "inkjet",
        "pages_per_minute": 22,
    }
    monitor: GenericPayload = {
        "kind": "device",
        "inventory_number": "PC-003",
        "manufacturer": "Dell",
        "country": "USA",
        "model": "U2723QE",
        "cost": 17200.5,
        "purchased_on": "2026-06-30",
    }

    return [computer, printer, monitor]


def fill_registry(container: Container) -> None:
    for device in sample_devices():
        container.registry.register(device)

    for payload in sample_payloads():
        container.registry.register(device_from_payload(payload))


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def run_oop_demo() -> None:
    container = build_container()
    registry = container.registry
    fill_registry(container)

    section("Registry as a collection (__len__, __iter__, __contains__)")
    print("Devices:", len(registry))
    print("PC-001 registered:", "PC-001" in registry)
    print("PC-999 registered:", "PC-999" in registry)

    for device in registry:
        print(" ", device)

    section("Search, filter, composition")
    print("registry['pc-002']:", registry["pc-002"])
    print("Dell devices:", [str(d.inventory_number) for d in registry.by_manufacturer("dell")])
    computers = registry.by_type(Computer)
    print("Computers (bound TypeVar):", [d.model for d in computers])
    print("Specifications:", computers[0].specifications())

    section("Statistics")
    print("Total cost:   ", registry.total_cost())
    print("Average cost: ", registry.average_cost())
    print("Most expensive:", registry.most_expensive())

    section("Encapsulation, value objects, errors")
    device = registry["PC-004"]

    for label, action in (
        ("negative cost", lambda: setattr(device, "cost", Money.of(-1))),
        ("other currency", lambda: setattr(device, "cost", Money.of(10, "USD"))),
        ("duplicate", lambda: registry.register(sample_devices()[0])),
        ("bad number", lambda: InventoryNumber("12")),
        ("unknown device", lambda: registry["PC-777"]),
        ("money mix", lambda: Money.of(1) + Money.of(1, "USD")),
    ):
        try:
            action()
        except DomainError as error:
            print(f"{label}: {type(error).__name__}: {error}")

    section("Maintenance service (strategy + DI)")
    due = container.maintenance.due_devices(TODAY)
    print("Due on", TODAY, ":", [str(d.inventory_number) for d in due])
    container.maintenance.notify_due(TODAY)
    container.maintenance.perform("PC-001", "Cleaning and update", TODAY, "I. Koval")
    due_after = container.maintenance.due_devices(TODAY)
    print("Due after PC-001 service:", [str(d.inventory_number) for d in due_after])

    section("Report service")
    print(container.reports.render())

    json_container = build_container(formatter=JsonReportFormatter())
    fill_registry(json_container)
    print("\nSame service, another formatter (JSON):")
    print(json_container.reports.render())

    section("TypedDict and runtime_checkable Protocol")
    print("Payload:", device_to_payload(registry["PC-004"]))
    print("Report is Serializable:", isinstance(container.reports.build_report(), Serializable))
    print("Money is Serializable:", isinstance(Money.of(1), Serializable))
    print("Device is Serializable:", isinstance(device, Serializable))


def run_oop_experiments() -> None:
    device = sample_devices()[0]

    section("Experiment 1: dependency injection")
    buffer = io.StringIO()

    with contextlib.redirect_stdout(buffer):
        AlertServiceA().alert(device)

    print("A: output can be checked only by hijacking stdout:")
    print("  captured =", buffer.getvalue().strip())
    notifier = InMemoryNotifier()
    AlertServiceB(notifier).alert(device)
    print("B: injected test double keeps messages in a list:")
    print("  messages =", notifier.messages)
    print("B with the real adapter, service code unchanged:")
    AlertServiceB(ConsoleNotifier()).alert(device)

    section("Experiment 2: inheritance vs composition")
    line = "PC-001; Lenovo; 28500"
    print("Inheritance, ',' :", CsvProcessor().process("PC-001, Lenovo, 28500"))
    print("Inheritance, ';' + upper (new subclass):", UpperSemicolonProcessor().process(line))
    composed = Processor(
        SeparatorParser(";"),
        CostValidator(),
        UpperFormatter(LabelFormatter()),
    )
    print("Composition, ';' + upper (new combination):", composed.process(line))
    print("Parser tested alone:", SeparatorParser(",").parse("a, b, c"))
