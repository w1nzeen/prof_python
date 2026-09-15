from collections import Counter, defaultdict, deque
from collections.abc import Callable
from time import perf_counter

from tech_manager.decorators import measure_time
from tech_manager.models import Tech

_search_history: deque[str] = deque(maxlen=5)


def search_by_model(tech_list: list[Tech], model: str) -> list[Tech]:
    _search_history.append(model)
    return [tech for tech in tech_list if tech.model.lower() == model.lower()]


def create_tech_index(tech_list: list[Tech]) -> dict[str, Tech]:
    return {tech.inventory_number: tech for tech in tech_list}


def get_search_history() -> tuple[str, ...]:
    return tuple(_search_history)


def sort_by_vendor(tech_list: list[Tech]) -> list[Tech]:
    return sorted(tech_list, key=lambda tech: tech.vendor.lower())


def sort_items(
    tech_list: list[Tech],
    key: Callable[[Tech], object],
    reverse: bool = False,
) -> list[Tech]:
    return sorted(tech_list, key=key, reverse=reverse)


def filter_by_price_range(tech_list: list[Tech], min_price: float, max_price: float) -> list[Tech]:
    return [tech for tech in tech_list if min_price <= tech.price <= max_price]


def filter_items(tech_list: list[Tech], predicate: Callable[[Tech], bool]) -> list[Tech]:
    return [tech for tech in tech_list if predicate(tech)]


def create_price_filter(min_price: float) -> Callable[[Tech], bool]:

    def predicate(tech: Tech) -> bool:
        return tech.price >= min_price

    return predicate


def create_type_filter(tech_type: str) -> Callable[[Tech], bool]:

    def predicate(tech: Tech) -> bool:
        return tech.type.lower() == tech_type.lower()

    return predicate


def get_unique_vendors(tech_list: list[Tech]) -> set[str]:
    return {tech.vendor for tech in tech_list}


def get_unique_types(tech_list: list[Tech]) -> set[str]:
    return {tech.type for tech in tech_list}


def group_by_type(tech_list: list[Tech]) -> dict[str, list[Tech]]:
    grouped: defaultdict[str, list[Tech]] = defaultdict(list)
    for tech in tech_list:
        grouped[tech.type].append(tech)
    return dict(grouped)


def group_by_vendor_and_type(tech_list: list[Tech]) -> dict[str, dict[str, list[Tech]]]:
    grouped: defaultdict[str, defaultdict[str, list[Tech]]] = defaultdict(lambda: defaultdict(list))
    for tech in tech_list:
        grouped[tech.vendor][tech.type].append(tech)
    return {vendor: dict(types_dict) for vendor, types_dict in grouped.items()}


def count_by_type(tech_list: list[Tech]) -> Counter:
    return Counter(tech.type for tech in tech_list)  


def count_by_vendor(tech_list: list[Tech]) -> Counter:
    return Counter(tech.vendor for tech in tech_list)  

@measure_time
def avg_price(tech_list: list[Tech]) -> float:
    if not tech_list:
        return 0.0
    total_price = sum(tech.price for tech in tech_list)  
    return total_price / len(tech_list)


def find_most_expensive_tech(tech_list: list[Tech]) -> Tech | None:
    if not tech_list:
        return None
    return max(tech_list, key=lambda tech: tech.price)


def find_cheapest_tech(tech_list: list[Tech]) -> Tech | None:
    if not tech_list:
        return None
    return min(tech_list, key=lambda tech: tech.price)


def price_of_all_tech(tech_list: list[Tech]) -> float:
    return sum(tech.price for tech in tech_list)


def average_of_values(*prices: float) -> float:
    if not prices:
        return 0.0
    return sum(prices) / len(prices)


def create_tech_record(**fields) -> dict:
    return dict(fields)


def process_pipeline(tech_list: list[Tech], *steps: Callable[[list[Tech]], list[Tech]]) -> list[Tech]:
    result = tech_list
    for step in steps:
        result = step(result)
    return result


def build_summary_report(tech_list: list[Tech]) -> dict:
    return {
        "total_items": len(tech_list),
        "total_value": price_of_all_tech(tech_list),
        "average_price": (sum(tech.price for tech in tech_list) / len(tech_list)) if tech_list else 0.0,
        "unique_vendors": get_unique_vendors(tech_list),
        "unique_types": get_unique_types(tech_list),
        "count_by_type": dict(count_by_type(tech_list)),
        "most_expensive": find_most_expensive_tech(tech_list),
    }

def benchmark_search(tech_list: list[Tech], inventory_number: str) -> dict[str, float]:
    start = perf_counter()
    for tech in tech_list:
        if tech.inventory_number == inventory_number:
            break
    list_time = perf_counter() - start

    index = create_tech_index(tech_list)
    start = perf_counter()
    index.get(inventory_number)
    dict_time = perf_counter() - start

    return {"list_search_seconds": list_time, "dict_search_seconds": dict_time}