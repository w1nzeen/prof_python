"""Input data: sample devices and a generator of large data sets."""

import random

from equipment_manager.models import Device

# tuple: fixed collections of values that must not change
DEVICE_TYPES: tuple[str, ...] = (
    "Laptop",
    "Monitor",
    "Printer",
    "Router",
    "Server",
    "Keyboard",
)

MANUFACTURERS: tuple[str, ...] = (
    "Lenovo",
    "Dell",
    "HP",
    "Asus",
    "Acer",
    "TP-Link",
)

# list: ordered, mutable collection of Device objects
DEVICES: list[Device] = [
    Device("PC-001", "Laptop", "Lenovo", "ThinkPad E14", 28500.00),
    Device("PC-002", "Laptop", "Dell", "Latitude 5440", 36900.00),
    Device("PC-003", "Monitor", "Dell", "U2723QE", 17200.50),
    Device("PC-004", "Printer", "HP", "LaserJet M111w", 4800.00),
    Device("PC-005", "Laptop", "Lenovo", "IdeaPad 3", 21300.00),
    Device("PC-006", "Router", "TP-Link", "Archer AX55", 3100.00),
    Device("PC-007", "Monitor", "Asus", "ProArt PA278", 14900.00),
    Device("PC-008", "Server", "HP", "ProLiant DL20", 74500.00),
    Device("PC-009", "Printer", "HP", "OfficeJet Pro 9010", 8700.00),
    Device("PC-010", "Laptop", "Asus", "Vivobook 15", 19800.00),
    Device("PC-011", "Monitor", "Lenovo", "ThinkVision T24", 6900.00),
    Device("PC-012", "Keyboard", "Dell", "KB216", 450.00),
]


def generate_devices(count: int, seed: int = 42) -> list[Device]:
    """Generate `count` reproducible devices for benchmarks."""
    rng = random.Random(seed)

    return [
        Device(
            inventory_number=f"PC-{number:06d}",
            device_type=rng.choice(DEVICE_TYPES),
            manufacturer=rng.choice(MANUFACTURERS),
            model=f"Model-{rng.randint(1, 99)}",
            cost=round(rng.uniform(300, 80000), 2),
        )
        for number in range(1, count + 1)
    ]
