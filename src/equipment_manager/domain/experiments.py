"""Design experiments: DI vs hard-coded dependency, inheritance vs composition."""

from dataclasses import dataclass
from typing import Protocol

from equipment_manager.domain.adapters import ConsoleNotifier
from equipment_manager.domain.exceptions import InvalidValueError
from equipment_manager.domain.models import Device
from equipment_manager.domain.protocols import Notifier

# ---------------------------------------------------------------- DI


class AlertServiceA:
    """Variant A: the service creates its concrete dependency itself."""

    def __init__(self) -> None:
        self.notifier = ConsoleNotifier()

    def alert(self, device: Device) -> None:
        self.notifier.send("it-support@example.com", f"Check {device}")


class AlertServiceB:
    """Variant B: dependency injection through an abstraction."""

    def __init__(self, notifier: Notifier) -> None:
        self.notifier = notifier

    def alert(self, device: Device) -> None:
        self.notifier.send("it-support@example.com", f"Check {device}")


# ------------------------------------------- inheritance (variant 1)


class BaseProcessor:
    """Template method: subclasses override the steps they need."""

    separator = ","

    def parse(self, line: str) -> list[str]:
        return [part.strip() for part in line.split(self.separator)]

    def validate(self, fields: list[str]) -> None:
        if len(fields) != 3:
            raise InvalidValueError("Expected 3 fields")

        float(fields[2])

    def format(self, fields: list[str]) -> str:
        return f"{fields[0]}: {fields[1]} ({fields[2]})"

    def process(self, line: str) -> str:
        fields = self.parse(line)
        self.validate(fields)

        return self.format(fields)


class CsvProcessor(BaseProcessor):
    separator = ","


class SemicolonProcessor(BaseProcessor):
    separator = ";"


class UpperSemicolonProcessor(SemicolonProcessor):
    """A new combination (';' + upper case) needs a new subclass."""

    def format(self, fields: list[str]) -> str:
        return super().format(fields).upper()


# ------------------------------------------- composition (variant 2)


class Parser(Protocol):
    def parse(self, line: str) -> list[str]: ...


class Validator(Protocol):
    def validate(self, fields: list[str]) -> None: ...


class Formatter(Protocol):
    def format(self, fields: list[str]) -> str: ...


class SeparatorParser:
    def __init__(self, separator: str) -> None:
        self.separator = separator

    def parse(self, line: str) -> list[str]:
        return [part.strip() for part in line.split(self.separator)]


class CostValidator:
    def validate(self, fields: list[str]) -> None:
        if len(fields) != 3:
            raise InvalidValueError("Expected 3 fields")

        float(fields[2])


class LabelFormatter:
    def format(self, fields: list[str]) -> str:
        return f"{fields[0]}: {fields[1]} ({fields[2]})"


class UpperFormatter:
    """Decorates another formatter instead of subclassing it."""

    def __init__(self, inner: Formatter) -> None:
        self.inner = inner

    def format(self, fields: list[str]) -> str:
        return self.inner.format(fields).upper()


@dataclass(frozen=True)
class Processor:
    """Has-a Parser, Validator and Formatter; any combination works."""

    parser: Parser
    validator: Validator
    formatter: Formatter

    def process(self, line: str) -> str:
        fields = self.parser.parse(line)
        self.validator.validate(fields)

        return self.formatter.format(fields)
