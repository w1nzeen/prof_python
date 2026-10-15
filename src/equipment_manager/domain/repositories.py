"""Generic in-memory repository."""

from collections.abc import Callable, Hashable
from typing import Generic, TypeVar

from equipment_manager.domain.exceptions import DuplicateKeyError

K = TypeVar("K", bound=Hashable)
T = TypeVar("T")


class InMemoryRepository(Generic[K, T]):
    """Stores items of any type T identified by a key of type K.

    The key is computed by `key_func`, so the repository knows nothing
    about devices and can be reused for other entities.
    """

    def __init__(self, key_func: Callable[[T], K]) -> None:
        self._key_func = key_func
        self._items: dict[K, T] = {}

    def add(self, item: T) -> None:
        key = self._key_func(item)

        if key in self._items:
            raise DuplicateKeyError(f"Item with key {key} already exists")

        self._items[key] = item

    def get(self, key: K) -> T | None:
        return self._items.get(key)

    def remove(self, key: K) -> bool:
        return self._items.pop(key, None) is not None

    def all(self) -> list[T]:
        return list(self._items.values())

    def keys(self) -> list[K]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, key: object) -> bool:
        return key in self._items
