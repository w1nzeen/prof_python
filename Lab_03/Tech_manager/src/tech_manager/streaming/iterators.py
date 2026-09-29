"""Власні iterator classes (iterable і iterator розділено)."""

from collections.abc import Iterator


class NumberRangeIterator:
    """Iterator: зберігає поточний стан обходу, є one-shot object."""

    def __init__(self, start: int, stop: int) -> None:
        self.current = start
        self.stop = stop

    def __iter__(self) -> "NumberRangeIterator":
        return self

    def __next__(self) -> int:
        if self.current >= self.stop:
            raise StopIteration
        value = self.current
        self.current += 1
        return value


class NumberRange:
    """Iterable: кожний виклик iter() створює новий незалежний iterator."""

    def __init__(self, start: int, stop: int) -> None:
        self.start = start
        self.stop = stop

    def __iter__(self) -> NumberRangeIterator:
        return NumberRangeIterator(self.start, self.stop)


class InventoryNumberIterator:
    """Iterator інвентарних номерів формату 000001, 000002, ..."""

    def __init__(self, start: int, stop: int, width: int) -> None:
        self._numbers = NumberRangeIterator(start, stop)
        self._width = width

    def __iter__(self) -> "InventoryNumberIterator":
        return self

    def __next__(self) -> str:
        return f"{next(self._numbers):0{self._width}d}"


class InventoryNumberRange:
    """Iterable інвентарних номерів; використовується генератором даних."""

    def __init__(self, start: int, stop: int, width: int = 6) -> None:
        self.start = start
        self.stop = stop
        self.width = width

    def __iter__(self) -> Iterator[str]:
        return InventoryNumberIterator(self.start, self.stop, self.width)
