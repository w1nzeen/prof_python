"""Benchmark: list vs dict vs set.

Запуск: python -m tech_manager.benchmark
"""

from time import perf_counter

from tech_manager.data import generate_tech_list
from tech_manager.processors import create_inventory_index, find_linear

SIZES: tuple[int, ...] = (1_000, 10_000, 100_000)


def average_time(func, repeats: int) -> float:
    """Середній час одного виклику func() у секундах."""
    start = perf_counter()
    for _ in range(repeats):
        func()
    return (perf_counter() - start) / repeats


def run_benchmark(size: int) -> dict[str, float]:
    tech_list = generate_tech_list(size)
    # Найгірший випадок для list - шуканий елемент в кінці.
    target = tech_list[-1].inventory_number

    start = perf_counter()
    index = create_inventory_index(tech_list)
    build_time = perf_counter() - start

    numbers_list = [tech.inventory_number for tech in tech_list]
    numbers_set = set(numbers_list)

    list_repeats = 200 if size <= 10_000 else 50
    return {
        "list_search": average_time(lambda: find_linear(tech_list, target), list_repeats),
        "dict_search": average_time(lambda: index.get(target), 100_000),
        "build_index": build_time,
        "in_list": average_time(lambda: target in numbers_list, list_repeats),
        "in_set": average_time(lambda: target in numbers_set, 100_000),
    }


def format_row(size: int, result: dict[str, float]) -> str:
    def us(value: float) -> str:
        return f"{value * 1e6:>12.3f}"

    return (
        f"{size:>9,} |"
        f"{us(result['list_search'])} |{us(result['dict_search'])} |"
        f"{us(result['build_index'])} |"
        f"{us(result['in_list'])} |{us(result['in_set'])}"
    )


def main() -> None:
    header = (
        f"{'records':>9} |{'list search':>12} |{'dict search':>12} |"
        f"{'build index':>12} |{'in list':>12} |{'in set':>12}"
    )
    print("Час, мікросекунди (us) на одну операцію")
    print(header)
    print("-" * len(header))
    for size in SIZES:
        print(format_row(size, run_benchmark(size)))


if __name__ == "__main__":
    main()
