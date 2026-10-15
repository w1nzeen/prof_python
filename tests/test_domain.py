from datetime import date

import pytest

from equipment_manager.domain.adapters import (
    InMemoryNotifier,
    JsonReportFormatter,
    TextReportFormatter,
)
from equipment_manager.domain.container import build_container
from equipment_manager.domain.demo import (
    TODAY,
    fill_registry,
    sample_devices,
    sample_payloads,
)
from equipment_manager.domain.dto import (
    device_from_payload,
    device_to_payload,
)
from equipment_manager.domain.exceptions import (
    CurrencyMismatchError,
    DeviceNotFoundError,
    DomainError,
    DuplicateKeyError,
    InvalidValueError,
    MaintenanceError,
)
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
from equipment_manager.domain.policies import (
    ByKindPolicy,
    FixedIntervalPolicy,
    MaintenancePolicy,
)
from equipment_manager.domain.protocols import Serializable
from equipment_manager.domain.repositories import InMemoryRepository
from equipment_manager.domain.value_objects import InventoryNumber, Money
from equipment_manager.exceptions import EquipmentError


def make_container(notifier: InMemoryNotifier | None = None):  # type: ignore[no-untyped-def]
    container = build_container(notifier=notifier or InMemoryNotifier())
    fill_registry(container)
    return container


# ---------------------------------------------------------- value objects
def test_money_rules() -> None:
    assert str(Money.of(10.456)) == "10.46 UAH"
    assert Money.of(1) + Money.of(2) == Money.of(3)
    assert Money.of(5) * 3 == Money.of(15)
    assert 3 * Money.of(5) == Money.of(15)
    assert Money.of(10) / 4 == Money.of("2.50")
    assert Money.of(1) < Money.of(2) <= Money.of(2)
    assert max(Money.of(1), Money.of(7)) == Money.of(7)

    with pytest.raises(InvalidValueError):
        Money.of(-1)
    with pytest.raises(InvalidValueError):
        Money.of("abc")
    with pytest.raises(InvalidValueError):
        Money.of("NaN")
    with pytest.raises(InvalidValueError):
        Money.of(1, "UA")
    with pytest.raises(CurrencyMismatchError):
        Money.of(1) + Money.of(1, "usd")
    with pytest.raises(CurrencyMismatchError):
        _ = Money.of(1) < Money.of(1, "USD")
    with pytest.raises(InvalidValueError):
        Money.of(1) / 0


def test_money_is_immutable_and_hashable() -> None:
    money = Money.of(5)

    with pytest.raises(AttributeError):
        money.amount = money.amount * 2  # type: ignore[misc]

    assert {money, Money.of(5)} == {money}
    assert Money.zero("usd").currency == "USD"


def test_inventory_number() -> None:
    assert str(InventoryNumber(" pc-001 ")) == "PC-001"
    assert InventoryNumber.parse("pc-1") == InventoryNumber("PC-1")
    number = InventoryNumber("PC-002")
    assert InventoryNumber.parse(number) is number

    for bad in ("", "12", "PC001", "PC-", "TOOLONG-1"):
        with pytest.raises(InvalidValueError):
            InventoryNumber(bad)


def test_exception_hierarchy() -> None:
    assert issubclass(DomainError, EquipmentError)
    assert issubclass(InvalidValueError, ValueError)
    assert issubclass(CurrencyMismatchError, InvalidValueError)
    assert issubclass(DeviceNotFoundError, LookupError)


# ---------------------------------------------------------------- models
def test_inheritance_and_class_attribute() -> None:
    devices = sample_devices()
    computer = devices[0]
    printer = devices[2]

    assert isinstance(computer, Device) and isinstance(printer, Device)
    assert (computer.kind, printer.kind, Device.kind) == (
        "Computer", "Printer", "Device",
    )
    assert computer.specifications()["RAM"] == "16 GB"
    assert printer.specifications()["Technology"] == "laser"


def test_device_encapsulation_and_dunders() -> None:
    computer = sample_devices()[0]

    with pytest.raises(AttributeError):
        computer.inventory_number = InventoryNumber("PC-777")  # type: ignore[misc]

    computer.cost = Money.of(30000)
    assert computer.cost == Money.of(30000)

    with pytest.raises(InvalidValueError):
        computer.cost = Money.of(1, "USD")

    assert "Computer(" in repr(computer) and "PC-001" in repr(computer)
    assert str(computer).startswith("PC-001 Computer: Lenovo ThinkPad E14")
    assert computer == sample_devices()[0]
    assert len({computer, sample_devices()[0]}) == 1


def test_validation_of_entities() -> None:
    base = {
        "inventory_number": InventoryNumber("PC-050"),
        "manufacturer": Manufacturer("HP"),
        "cost": Money.of(1),
        "purchased_on": date(2025, 1, 1),
    }

    with pytest.raises(InvalidValueError):
        Device(model=" ", **base)  # type: ignore[arg-type]
    with pytest.raises(InvalidValueError):
        Computer(model="X", cpu="c", ram_gb=0, storage_gb=1, **base)  # type: ignore[arg-type]
    with pytest.raises(InvalidValueError):
        Printer(
            model="X", technology=PrintTechnology.LASER,
            pages_per_minute=0, **base,  # type: ignore[arg-type]
        )
    with pytest.raises(InvalidValueError):
        Manufacturer("  ")


def test_maintenance_history() -> None:
    computer = sample_devices()[0]
    assert computer.last_service_date == date(2025, 1, 15)

    container = make_container()
    record = container.maintenance.perform("PC-001", "Cleaning", TODAY, "Ann")
    device = container.registry["PC-001"]
    assert device.maintenance_history == (record,)
    assert device.last_service_date == TODAY

    with pytest.raises(MaintenanceError):
        container.maintenance.perform("PC-001", "Too early", date(2020, 1, 1))
    with pytest.raises(InvalidValueError):
        container.maintenance.perform("PC-001", " ", TODAY)


# -------------------------------------------------------------- registry
def test_registry_collection_protocol() -> None:
    registry = make_container().registry

    assert len(registry) == 6
    assert "pc-001" in registry and InventoryNumber("PC-001") in registry
    assert "PC-999" not in registry and "bad" not in registry and 5 not in registry
    assert registry["PC-002"].model == "Latitude 5440"
    assert len(list(registry)) == 6

    with pytest.raises(DeviceNotFoundError):
        registry["PC-999"]
    with pytest.raises(DuplicateKeyError):
        registry.register(sample_devices()[0])

    assert registry.unregister("PC-003") is True
    assert registry.unregister("PC-003") is False
    assert len(registry) == 5


def test_registry_search_and_statistics() -> None:
    registry = make_container().registry

    dell = registry.by_manufacturer(" DELL ")
    assert sorted(str(d.inventory_number) for d in dell) == ["PC-002", "PC-003"]
    assert [type(d) for d in registry.by_type(Computer)] == [Computer] * 3
    assert registry.total_cost() == Money.of("117400.50")
    assert registry.average_cost() == Money.of("19566.75")
    best = registry.most_expensive()
    assert best is not None and str(best.inventory_number) == "PC-002"
    assert registry.count_by_manufacturer() == {"Lenovo": 2, "HP": 2, "Dell": 2}
    assert registry.count_by_kind() == {"Computer": 3, "Printer": 2, "Device": 1}


def test_empty_registry() -> None:
    registry = build_container().registry
    assert registry.average_cost() == Money.zero()
    assert registry.total_cost() == Money.zero()
    assert registry.most_expensive() is None


def test_generic_repository() -> None:
    repository = InMemoryRepository[str, int](lambda value: str(value))
    repository.add(1)
    repository.add(2)
    assert repository.get("1") == 1 and "2" in repository
    assert repository.keys() == ["1", "2"] and len(repository) == 2
    assert repository.remove("1") and not repository.remove("1")
    with pytest.raises(DuplicateKeyError):
        repository.add(2)


# ------------------------------------------------------------------- dto
def test_payload_round_trip() -> None:
    for payload in sample_payloads():
        device = device_from_payload(payload)
        assert device_to_payload(device) == {
            "country": "USA", "currency": "UAH", **payload,
        }

    for device in sample_devices():
        assert device_from_payload(device_to_payload(device)) == device


def test_payload_errors() -> None:
    good = sample_payloads()[0]

    for broken in (
        {**good, "inventory_number": "bad"},
        {**good, "purchased_on": "yesterday"},
        {**good, "cost": "abc"},
        {**good, "ram_gb": -1},
    ):
        with pytest.raises(InvalidValueError):
            device_from_payload(broken)  # type: ignore[arg-type]

    missing = {k: v for k, v in good.items() if k != "cpu"}
    with pytest.raises(InvalidValueError):
        device_from_payload(missing)  # type: ignore[arg-type]

    printer = {**sample_payloads()[1], "technology": "laser3d"}
    with pytest.raises(InvalidValueError):
        device_from_payload(printer)  # type: ignore[arg-type]


# -------------------------------------------------------------- services
def test_policies() -> None:
    policy = ByKindPolicy(
        {Computer: FixedIntervalPolicy(10), Device: FixedIntervalPolicy(20)},
        default=FixedIntervalPolicy(30),
    )
    computer, _, printer = sample_devices()

    assert policy.interval_for(computer) == 10
    assert policy.interval_for(printer) == 20  # found through base class
    assert ByKindPolicy({}, FixedIntervalPolicy(5)).interval_for(printer) == 5
    assert policy.next_due(computer) == date(2025, 1, 25)
    assert policy.is_due(computer, date(2025, 1, 25))
    assert not policy.is_due(computer, date(2025, 1, 24))

    with pytest.raises(InvalidValueError):
        FixedIntervalPolicy(0)
    with pytest.raises(TypeError):
        MaintenancePolicy()  # type: ignore[abstract]


def test_maintenance_service_with_test_double() -> None:
    notifier = InMemoryNotifier()
    container = make_container(notifier)
    service = container.maintenance

    due = service.due_devices(TODAY)
    assert sorted(str(d.inventory_number) for d in due) == [
        "PC-001", "PC-002", "PC-004", "PC-005", "PC-009",
    ]
    assert service.notify_due(TODAY) == 5
    assert len(notifier.messages) == 5
    service.perform("PC-001", "Cleaning", TODAY)
    assert "PC-001" not in [str(d.inventory_number) for d in service.due_devices(TODAY)]
    assert "Maintenance done" in notifier.messages[-1][1]


def test_report_service_and_formatters() -> None:
    container = make_container()
    report = container.reports.build_report()

    assert report.total_devices == 6
    assert report.total_cost == Money.of("117400.50")
    as_object: object = report
    assert isinstance(as_object, Serializable)
    assert isinstance(Money.of(1), Serializable)
    assert not isinstance(sample_devices()[0], Serializable)

    text = TextReportFormatter().format(report)
    assert "Devices:        6" in text and "Dell: 2" in text
    assert '"total_devices": 6' in JsonReportFormatter().format(report)

    other = build_container(formatter=JsonReportFormatter(indent=0))
    fill_registry(other)
    assert other.reports.render().startswith("{")


# ----------------------------------------------------------- experiments
def test_di_experiment(capsys: pytest.CaptureFixture[str]) -> None:
    device = sample_devices()[0]
    notifier = InMemoryNotifier()
    AlertServiceB(notifier).alert(device)
    assert notifier.messages and "Check PC-001" in notifier.messages[0][1]

    AlertServiceA().alert(device)  # can only be checked through stdout
    assert "Check PC-001" in capsys.readouterr().out


def test_inheritance_vs_composition_give_same_result() -> None:
    line = "PC-001; Lenovo; 28500"
    composed = Processor(
        SeparatorParser(";"), CostValidator(), UpperFormatter(LabelFormatter())
    )
    assert composed.process(line) == UpperSemicolonProcessor().process(line)
    assert CsvProcessor().process("a, b, 1") == "a: b (1)"

    with pytest.raises(InvalidValueError):
        CsvProcessor().process("a, b")
    with pytest.raises(InvalidValueError):
        composed.process("a;b")
