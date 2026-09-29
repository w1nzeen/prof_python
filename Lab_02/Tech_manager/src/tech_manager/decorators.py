"""Декоратори: вимірювання часу та журнал останніх операцій."""

from collections import deque
from collections.abc import Callable
from functools import wraps
from time import perf_counter
from typing import Any

# deque з maxlen автоматично відкидає найстаріші записи: append/popleft - O(1).
OPERATION_HISTORY: deque[str] = deque(maxlen=5)


def measure_time(func: Callable[..., Any]) -> Callable[..., Any]:
    """Простий декоратор: друкує час виконання функції."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = perf_counter()
        result = func(*args, **kwargs)
        elapsed = perf_counter() - start
        print(f"{func.__name__}: {elapsed:.8f} s")
        return result

    return wrapper


def log_operation(
    history: deque[str],
    label: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Параметризований декоратор (closure + decorator).

    Записує назву операції в `history` (deque) при кожному виклику.
    Параметри `history` і `label` запам'ятовуються через closure.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        operation_name = label or func.__name__

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            history.append(operation_name)
            return func(*args, **kwargs)

        return wrapper

    return decorator
