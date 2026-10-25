"""Experiment 5: a flaky test and its deterministic replacement.

test_random_bad fails about half of the runs. Run it with:
    python experiments/lab6/run_repeatedly.py experiments/lab6/test_exp5_flaky.py::test_random_bad 20
"""

import random

import pytest


def pick_inventory_slot() -> int:
    return random.randint(1, 2)


def test_random_bad() -> None:
    assert pick_inventory_slot() == 1  # depends on randomness: flaky


def test_random_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(random, "randint", lambda low, high: low)

    assert pick_inventory_slot() == 1


def test_random_with_seeded_generator() -> None:
    generator = random.Random(2026)
    first = [generator.randint(1, 2) for _ in range(5)]
    generator = random.Random(2026)

    assert [generator.randint(1, 2) for _ in range(5)] == first
