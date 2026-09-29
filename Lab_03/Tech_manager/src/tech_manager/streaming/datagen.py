"""Генерація великого тестового файлу (CSV) з частиною некоректних рядків."""

import csv
import random
from pathlib import Path

from tech_manager.data import TECH_TYPES, VENDORS
from tech_manager.streaming.iterators import InventoryNumberRange
from tech_manager.streaming.records import CSV_FIELDS


def generate_test_file(
    path: Path,
    count: int,
    seed: int = 42,
    invalid_ratio: float = 0.01,
) -> Path:
    """Записує `count` рядків. Приблизно invalid_ratio з них - некоректні,
    ~2% мають "брудний" регістр/пробіли (для transformation stage).
    """
    rng = random.Random(seed)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_FIELDS)
        for number in InventoryNumberRange(1, count + 1):
            tech_type = rng.choice(TECH_TYPES)
            vendor = rng.choice(VENDORS)
            model = f"Model-{rng.randint(1, 500)}"
            cost: object = round(rng.uniform(100, 3000), 2)

            roll = rng.random()
            if roll < invalid_ratio:
                kind = rng.randrange(3)
                if kind == 0:
                    cost = "N/A"
                elif kind == 1:
                    cost = -cost  # type: ignore[operator]
                else:
                    model = ""
            elif roll < invalid_ratio + 0.02:
                tech_type = f" {tech_type.lower()} "

            writer.writerow([number, tech_type, vendor, model, cost])
    return path
