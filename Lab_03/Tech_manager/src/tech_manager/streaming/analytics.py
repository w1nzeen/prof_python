"""Aggregation stage: потокові обчислення без матеріалізації даних."""

from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import accumulate, groupby, pairwise

from tech_manager.streaming.records import TechRecord


def streaming_total(records: Iterable[TechRecord]) -> float:
    """Загальна вартість обладнання (generator expression)."""
    return sum(record.cost for record in records)


def streaming_average(records: Iterable[TechRecord]) -> float:
    """Середня вартість за один прохід; пам'ять O(1)."""
    total = 0.0
    count = 0
    for record in records:
        total += record.cost
        count += 1
    return total / count if count else 0.0


def find_most_expensive(records: Iterable[TechRecord]) -> TechRecord | None:
    """Найдорожчий пристрій за один прохід."""
    return max(records, key=lambda record: record.cost, default=None)


def count_by_type(records: Iterable[TechRecord]) -> Counter[str]:
    return Counter(record.type for record in records)


def count_by_manufacturer(records: Iterable[TechRecord]) -> Counter[str]:
    return Counter(record.manufacturer for record in records)


@dataclass(frozen=True)
class StreamStatistics:
    count: int
    total: float
    average: float
    minimum: float | None
    maximum: float | None
    most_expensive: TechRecord | None
    by_type: dict[str, int]
    by_manufacturer: dict[str, int]


def calculate_statistics(records: Iterable[TechRecord]) -> StreamStatistics:
    """Уся статистика за ОДИН прохід по потоку."""
    count = 0
    total = 0.0
    minimum: float | None = None
    maximum: float | None = None
    most_expensive: TechRecord | None = None
    by_type: Counter[str] = Counter()
    by_manufacturer: Counter[str] = Counter()

    for record in records:
        cost = record.cost
        count += 1
        total += cost
        by_type[record.type] += 1
        by_manufacturer[record.manufacturer] += 1
        if minimum is None or cost < minimum:
            minimum = cost
        if maximum is None or cost > maximum:
            maximum = cost
            most_expensive = record

    return StreamStatistics(
        count=count,
        total=total,
        average=total / count if count else 0.0,
        minimum=minimum,
        maximum=maximum,
        most_expensive=most_expensive,
        by_type=dict(by_type),
        by_manufacturer=dict(by_manufacturer),
    )


def cumulative_cost(records: Iterable[TechRecord]) -> Iterator[float]:
    """Накопичувальна вартість (itertools.accumulate)."""
    return (round(value, 2) for value in accumulate(r.cost for r in records))


def cost_differences(records: Iterable[TechRecord]) -> Iterator[float]:
    """Різниця вартості сусідніх записів (itertools.pairwise)."""
    return (round(b.cost - a.cost, 2) for a, b in pairwise(records))


def cost_by_manufacturer(
    records: Iterable[TechRecord],
) -> Iterator[tuple[str, int, float]]:
    """groupby: потребує попереднього сортування за тим самим key.

    Увага: sorted() матеріалізує дані, тому використовувати для невеликих потоків.
    """

    def key(record: TechRecord) -> str:
        return record.manufacturer.lower()

    for _, group in groupby(sorted(records, key=key), key=key):
        members = list(group)
        yield (
            members[0].manufacturer,
            len(members),
            round(sum(m.cost for m in members), 2),
        )
