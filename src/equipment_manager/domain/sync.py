"""Asynchronous synchronisation with an external inventory provider."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Protocol

from equipment_manager.domain.dto import DevicePayload, device_from_payload
from equipment_manager.domain.exceptions import (
    DuplicateKeyError,
    InvalidValueError,
    InventorySyncError,
)
from equipment_manager.domain.models import InventoryRegistry

logger = logging.getLogger(__name__)


class InventoryProvider(Protocol):
    """External source of equipment data (REST API, ERP, ...)."""

    async def fetch_devices(self) -> list[DevicePayload]: ...


@dataclass(frozen=True)
class SyncResult:
    added: int
    duplicates: int
    rejected: int


class InventorySyncService:
    """Loads devices from a provider into the registry."""

    def __init__(
        self,
        provider: InventoryProvider,
        registry: InventoryRegistry,
    ) -> None:
        self._provider = provider
        self._registry = registry

    async def sync(self, timeout: float | None = None) -> SyncResult:
        """Add new devices; duplicates and invalid payloads are skipped.

        Provider failures leave the registry untouched and are reported
        as InventorySyncError (the original error is kept as the cause).
        """
        try:
            payloads = await asyncio.wait_for(
                self._provider.fetch_devices(), timeout
            )
        except (ConnectionError, TimeoutError, OSError) as error:
            raise InventorySyncError("Inventory provider failed") from error

        added = duplicates = rejected = 0

        for payload in payloads:
            try:
                device = device_from_payload(payload)
                self._registry.register(device)
            except DuplicateKeyError:
                duplicates += 1
            except InvalidValueError as error:
                rejected += 1
                logger.warning("Rejected payload: %s", error)
            else:
                added += 1

        return SyncResult(added, duplicates, rejected)
