"""Functions with several branches: used by experiment 3."""


def classify_cost(cost: float) -> str:
    if cost >= 30000:
        return "premium"

    if cost >= 10000:
        return "standard"

    return "budget"


def warranty_label(extended: bool) -> str:
    label = "standard"

    if extended:
        label = "extended"

    return label
