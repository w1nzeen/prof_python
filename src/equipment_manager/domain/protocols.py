"""Small structural interfaces (interface segregation)."""

from typing import TYPE_CHECKING, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from equipment_manager.domain.dto import InventoryReport

K = TypeVar("K")
T = TypeVar("T")


class Repository(Protocol[K, T]):
    """Storage of items identified by a key."""

    def add(self, item: T) -> None: ...

    def get(self, key: K) -> T | None: ...

    def remove(self, key: K) -> bool: ...

    def all(self) -> list[T]: ...

    def keys(self) -> list[K]: ...


class Notifier(Protocol):
    """Sends a message to a recipient."""

    def send(self, recipient: str, message: str) -> None: ...


class ReportFormatter(Protocol):
    """Turns a report DTO into text."""

    def format(self, report: "InventoryReport") -> str: ...


@runtime_checkable
class Serializable(Protocol):
    """Anything that can be converted to a plain dictionary."""

    def to_dict(self) -> dict[str, object]: ...
