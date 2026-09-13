from tech_manager.models import Tech

def search_by_model(tech_list: list[Tech], model: str) -> list[Tech]:
    return [tech for tech in tech_list if tech.model.lower() == model.lower()]


def sort_by_vendor(tech_list: list[Tech]) -> list[Tech]:
    return sorted(tech_list, key=lambda tech: tech.vendor.lower())


def avg_price(tech_list: list[Tech]) -> float:
    if not tech_list:
        return 0.0
    total_price = sum(tech.price for tech in tech_list)
    return total_price / len(tech_list)

def find_most_expensive_tech(tech_list: list[Tech]) -> Tech:
    if not tech_list:
        return None
    return max(tech_list, key=lambda tech: tech.price)

def filter_by_price_range(tech_list: list[Tech], min_price: float, max_price: float) -> list[Tech]:
    return [tech for tech in tech_list if min_price <= tech.price <= max_price]

def price_of_all_tech(tech_list: list[Tech]) -> float:
    return sum(tech.price for tech in tech_list)