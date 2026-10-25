"""Experiment 3, step 1: only two of the three classes and one flag value."""

from branch_code import classify_cost, warranty_label


def test_premium() -> None:
    assert classify_cost(35000) == "premium"


def test_standard() -> None:
    assert classify_cost(20000) == "standard"


def test_extended_warranty() -> None:
    assert warranty_label(True) == "extended"
