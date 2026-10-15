"""Concrete implementations of the protocols (infrastructure)."""

import json

from equipment_manager.domain.dto import InventoryReport


class ConsoleNotifier:
    """Prints notifications; does not inherit Notifier explicitly."""

    def send(self, recipient: str, message: str) -> None:
        print(f"Notification to {recipient}: {message}")


class InMemoryNotifier:
    """Collects messages; convenient for tests."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def send(self, recipient: str, message: str) -> None:
        self.messages.append((recipient, message))


class TextReportFormatter:
    def format(self, report: InventoryReport) -> str:
        lines = [
            "Inventory report",
            f"  Devices:        {report.total_devices}",
            f"  Total cost:     {report.total_cost}",
            f"  Average cost:   {report.average_cost}",
            f"  Most expensive: {report.most_expensive or '-'}",
            "  By manufacturer:",
        ]
        lines += [
            f"    {name}: {count}"
            for name, count in sorted(report.by_manufacturer.items())
        ]
        lines.append("  By kind:")
        lines += [
            f"    {kind}: {count}"
            for kind, count in sorted(report.by_kind.items())
        ]

        return "\n".join(lines)


class JsonReportFormatter:
    def __init__(self, indent: int = 2) -> None:
        self.indent = indent

    def format(self, report: InventoryReport) -> str:
        return json.dumps(
            report.to_dict(),
            ensure_ascii=False,
            indent=self.indent,
        )
