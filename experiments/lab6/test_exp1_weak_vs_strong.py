"""Experiment 1: weak and strong tests against a correct and a buggy function."""

import pytest

from sample_code import depreciate, depreciate_buggy

IMPLEMENTATIONS = [
    pytest.param(depreciate, id="correct"),
    pytest.param(depreciate_buggy, id="buggy"),
]


@pytest.mark.parametrize("function", IMPLEMENTATIONS)
def test_depreciation_weak(function) -> None:  # type: ignore[no-untyped-def]
    function(1000, 10)  # executes the code, verifies nothing


@pytest.mark.parametrize(
    "function",
    [
        pytest.param(depreciate, id="correct"),
        pytest.param(
            depreciate_buggy,
            id="buggy",
            marks=pytest.mark.xfail(strict=True, reason="intentional defect"),
        ),
    ],
)
def test_depreciation_strong(function) -> None:  # type: ignore[no-untyped-def]
    assert function(1000, 10) == pytest.approx(900)
