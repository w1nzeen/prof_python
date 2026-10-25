"""Sample functions for the testing experiments (not part of the project)."""


def depreciate(cost: float, percent: float) -> float:
    """Correct: value of equipment after depreciation."""
    return cost * (1 - percent / 100)


def depreciate_buggy(cost: float, percent: float) -> float:
    """BUG: returns the depreciation amount instead of the remaining value."""
    return cost * percent / 100
