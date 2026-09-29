"""Обробка колекцій: унікальні значення, індекси, групування, фільтри, пошук."""

from collections import Counter, defaultdict
from collections.abc import Callable
from typing import Any

from tech_manager.decorators import OPERATION_HISTORY, log_operation
from tech_manager.models import Tech

Predicate = Callable[[Tech], bool]


# --------------------------------------------------------------------------
# Унікальні значення (set comprehension)
# --------------------------------------------------------------------------
def get_unique_vendors(tech_list: list[Tech]) -> set[str]:
    """Унікальні виробники. Складність: O(n)."""
    return {tech.vendor for tech in tech_list}


def get_unique_types(tech_list: list[Tech]) -> set[str]:
    """Унікальні типи пристроїв. Складність: O(n)."""
    return {tech.type for tech in tech_list}


# --------------------------------------------------------------------------
# Індекс (dict comprehension) та пошук
# --------------------------------------------------------------------------
def create_inventory_index(tech_list: list[Tech]) -> dict[str, Tech]:
    """dict-index за інвентарним номером. Побудова: O(n)."""
    return {tech.inventory_number: tech for tech in tech_list}


@log_operation(OPERATION_HISTORY, label="find_by_inventory_number")
def find_by_inventory_number(
    index: dict[str, Tech],
    inventory_number: str,
) -> Tech | None:
    """Пошук за інвентарним номером через dict. Складність: O(1) в середньому."""
    return index.get(inventory_number)


def find_linear(tech_list: list[Tech], inventory_number: str) -> Tech | None:
    """Лінійний пошук у list (для порівняння з dict). Складність: O(n)."""
    for tech in tech_list:
        if tech.inventory_number == inventory_number:
            return tech
    return None


def create_tech(**fields: Any) -> Tech:
    """Створює Tech з довільних keyword-аргументів (**kwargs)."""
    fields["price"] = float(fields["price"])
    return Tech(**fields)


@log_operation(OPERATION_HISTORY)
def search_tech(tech_list: list[Tech], **criteria: str) -> list[Tech]:
    """Пошук за довільним набором полів (**kwargs), регістр не враховується.

    Приклад: search_tech(items, vendor="dell", type="laptop").
    Складність: O(n * k), k - кількість критеріїв.
    """
    return [
        tech
        for tech in tech_list
        if all(
            str(getattr(tech, field)).lower() == value.lower()
            for field, value in criteria.items()
        )
    ]


# --------------------------------------------------------------------------
# Фільтрація: універсальна функція + closures
# --------------------------------------------------------------------------
def filter_items(items: list[Tech], predicate: Predicate) -> list[Tech]:
    """Універсальна фільтрація (функція вищого порядку). Складність: O(n)."""
    return [item for item in items if predicate(item)]


def create_vendor_filter(*vendors: str) -> Predicate:
    """Closure: запам'ятовує множину виробників (*args)."""
    allowed = {vendor.lower() for vendor in vendors}

    def predicate(tech: Tech) -> bool:
        return tech.vendor.lower() in allowed  # O(1) для set

    return predicate


def create_price_filter(minimum: float, maximum: float) -> Predicate:
    """Closure: запам'ятовує межі цінового діапазону."""

    def predicate(tech: Tech) -> bool:
        return minimum <= tech.price <= maximum

    return predicate


@log_operation(OPERATION_HISTORY)
def filter_by_vendor(tech_list: list[Tech], *vendors: str) -> list[Tech]:
    """Фільтрація за одним або кількома виробниками."""
    return filter_items(tech_list, create_vendor_filter(*vendors))


# --------------------------------------------------------------------------
# Групування
# --------------------------------------------------------------------------
def group_by(
    tech_list: list[Tech],
    key: Callable[[Tech], str],
) -> dict[str, list[Tech]]:
    """Універсальне групування через defaultdict. Складність: O(n)."""
    groups: defaultdict[str, list[Tech]] = defaultdict(list)
    for tech in tech_list:
        groups[key(tech)].append(tech)
    return dict(groups)


def group_by_vendor(tech_list: list[Tech]) -> dict[str, list[Tech]]:
    return group_by(tech_list, key=lambda tech: tech.vendor)


def group_by_type(tech_list: list[Tech]) -> dict[str, list[Tech]]:
    return group_by(tech_list, key=lambda tech: tech.type)


def group_by_vendor_and_type(
    tech_list: list[Tech],
) -> dict[str, dict[str, list[Tech]]]:
    """Вкладене групування: виробник -> тип -> список пристроїв."""
    return {
        vendor: group_by_type(items)
        for vendor, items in group_by_vendor(tech_list).items()
    }


def count_by_type(tech_list: list[Tech]) -> Counter[str]:
    """Counter типів пристроїв (generator expression). Складність: O(n)."""
    return Counter(tech.type for tech in tech_list)


# --------------------------------------------------------------------------
# Сортування та pipeline
# --------------------------------------------------------------------------
def sort_items(
    items: list[Tech],
    key: Callable[[Tech], Any],
    reverse: bool = False,
) -> list[Tech]:
    """Універсальне сортування. Складність: O(n log n)."""
    return sorted(items, key=key, reverse=reverse)


def sort_by_price(tech_list: list[Tech], reverse: bool = True) -> list[Tech]:
    return sort_items(tech_list, key=lambda tech: tech.price, reverse=reverse)


def pipeline(
    items: list[Tech],
    *steps: Callable[[list[Tech]], list[Tech]],
) -> list[Tech]:
    """Послідовно застосовує кроки обробки: items -> step1 -> step2 -> ..."""
    for step in steps:
        items = step(items)
    return items
