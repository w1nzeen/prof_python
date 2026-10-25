"""Function with a defect: used by experiment 2."""


def total_with_vat(costs: list[float], vat_percent: float) -> float:
    """BUG: VAT is subtracted instead of being added."""
    total = sum(costs)

    if vat_percent > 0:
        return total * (1 - vat_percent / 100)

    return total
