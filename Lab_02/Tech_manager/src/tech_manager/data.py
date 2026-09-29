"""Вхідні дані: демонстраційний список техніки та генератор для benchmark."""

import random

from tech_manager.models import Tech

# Межі цінового діапазону для демонстрації фільтрації (tuple).
DEMO_PRICE_RANGE: tuple[float, float] = (600.0, 1000.0)

TECH_TYPES: tuple[str, ...] = ("Laptop", "Smartphone", "Tablet", "Monitor")
VENDORS: tuple[str, ...] = ("Dell", "Apple", "Samsung", "HP", "Google", "Lenovo")


def create_demo_tech_list() -> list[Tech]:
    """Повертає демонстраційний список (перші 5 позицій - з Lab 01)."""
    return [
        Tech("001", "Laptop", "Dell", "XPS 13", 999.99),
        Tech("002", "Smartphone", "Apple", "iPhone 13", 799.99),
        Tech("003", "Tablet", "Samsung", "Galaxy Tab S7", 649.99),
        Tech("004", "Laptop", "HP", "Spectre x360", 1199.99),
        Tech("005", "Smartphone", "Google", "Pixel 6", 599.99),
        Tech("006", "Laptop", "Dell", "Latitude 5440", 1149.00),
        Tech("007", "Monitor", "Dell", "U2723QE", 519.50),
        Tech("008", "Laptop", "Lenovo", "ThinkPad X1", 1899.00),
        Tech("009", "Smartphone", "Samsung", "Galaxy S23", 849.00),
        Tech("010", "Tablet", "Apple", "iPad Air", 599.00),
        Tech("011", "Monitor", "HP", "E24 G5", 189.90),
        Tech("012", "Smartphone", "Google", "Pixel 7", 649.00),
    ]


def generate_tech_list(count: int, seed: int = 42) -> list[Tech]:
    """Генерує `count` пристроїв з унікальними інвентарними номерами.

    Використовується у benchmark. seed робить результат відтворюваним.
    """
    rng = random.Random(seed)
    return [
        Tech(
            inventory_number=f"{number:06d}",
            type=rng.choice(TECH_TYPES),
            vendor=rng.choice(VENDORS),
            model=f"Model-{rng.randint(1, 500)}",
            price=round(rng.uniform(100, 3000), 2),
        )
        for number in range(1, count + 1)
    ]
