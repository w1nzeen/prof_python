"""Experiment 2: 100% coverage with a weak test hides a defect."""

import pytest

from vat_code import total_with_vat


def test_total_with_vat_executes_every_line() -> None:
    total_with_vat([100, 200], 20)
    total_with_vat([100, 200], 0)


@pytest.mark.xfail(strict=True, reason="intentional defect: VAT is subtracted")
def test_total_with_vat_with_a_meaningful_assertion() -> None:
    assert total_with_vat([100, 200], 20) == pytest.approx(360)


def test_total_without_vat_is_correct() -> None:
    assert total_with_vat([100, 200], 0) == pytest.approx(300)
