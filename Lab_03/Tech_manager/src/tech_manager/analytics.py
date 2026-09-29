"""Агрегація та статистика."""

import json
from pathlib import Path
from typing import Any

from tech_manager.decorators import measure_time
from tech_manager.models import Tech
from tech_manager.processors import count_by_type, get_unique_vendors, group_by_vendor


def calculate_average_values(*values: float) -> float:
    """Середнє довільної кількості чисел (*args)."""
    if not values:
        return 0.0
    return sum(values) / len(values)


@measure_time
def calculate_average_price(tech_list: list[Tech]) -> float:
    """Середня вартість. Складність: O(n)."""
    return calculate_average_values(*(tech.price for tech in tech_list))


def calculate_total_price(tech_list: list[Tech]) -> float:
    """Сумарна вартість обладнання (generator expression). Складність: O(n)."""
    return sum(tech.price for tech in tech_list)


def find_most_expensive(tech_list: list[Tech]) -> Tech | None:
    """Найдорожчий пристрій. Складність: O(n)."""
    if not tech_list:
        return None
    return max(tech_list, key=lambda tech: tech.price)


def get_price_range(tech_list: list[Tech]) -> tuple[float, float]:
    """Повертає tuple (мінімальна, максимальна) ціна."""
    if not tech_list:
        return (0.0, 0.0)
    prices = [tech.price for tech in tech_list]
    return (min(prices), max(prices))


def total_price_by_vendor(tech_list: list[Tech]) -> dict[str, float]:
    """Сумарна вартість техніки кожного виробника (dict comprehension)."""
    return {
        vendor: round(calculate_total_price(items), 2)
        for vendor, items in group_by_vendor(tech_list).items()
    }


def build_summary(tech_list: list[Tech]) -> dict[str, Any]:
    """Зведена статистика по обладнанню."""
    most_expensive = find_most_expensive(tech_list)
    minimum, maximum = get_price_range(tech_list)
    return {
        "count": len(tech_list),
        "unique_vendors": sorted(get_unique_vendors(tech_list)),
        "count_by_type": dict(count_by_type(tech_list)),
        "average_price": round(
            calculate_average_values(*(t.price for t in tech_list)), 2
        ),
        "total_price": round(calculate_total_price(tech_list), 2),
        "min_price": minimum,
        "max_price": maximum,
        "most_expensive": most_expensive.name if most_expensive else None,
        "total_price_by_vendor": total_price_by_vendor(tech_list),
    }


def export_summary(summary: dict[str, Any], path: str | Path) -> Path:
    """Зберігає summary у JSON-файл."""
    target = Path(path)
    target.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target
