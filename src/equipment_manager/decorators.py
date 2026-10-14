"""Decorators used by the data processing modules."""

from collections import deque
from collections.abc import Callable
from functools import wraps
from time import perf_counter
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

HISTORY_SIZE = 5

# The last operations are stored in a deque: when it is full,
# appending a new item automatically removes the oldest one (O(1)).
OPERATION_HISTORY: deque[str] = deque(maxlen=HISTORY_SIZE)


def measure_time(func: Callable[P, R]) -> Callable[P, R]:
    """Print how long the decorated function was running."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = perf_counter()
        result = func(*args, **kwargs)
        elapsed = perf_counter() - start

        print(f"{func.__name__}: {elapsed:.8f} s")

        return result

    return wrapper


def record_operation(
    history: deque[str],
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Parameterized decorator: remember the name of every call."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            history.append(func.__name__)
            return func(*args, **kwargs)

        return wrapper

    return decorator
