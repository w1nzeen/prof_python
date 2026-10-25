"""Experiment 3, step 2: every branch is exercised."""

import pytest

from branch_code import classify_cost, warranty_label


@pytest.mark.parametrize(
    ("cost", "expected"),
    [
        (35000, "premium"),
        (30000, "premium"),
        (29999.99, "standard"),
        (10000, "standard"),
        (9999.99, "budget"),
        (0, "budget"),
    ],
)
def test_classify_cost(cost: float, expected: str) -> None:
    assert classify_cost(cost) == expected


@pytest.mark.parametrize(("extended", "expected"), [(True, "extended"), (False, "standard")])
def test_warranty_label(extended: bool, expected: str) -> None:
    assert warranty_label(extended) == expected
