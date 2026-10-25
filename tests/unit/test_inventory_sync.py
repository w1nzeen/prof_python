"""Asynchronous inventory provider tested with AsyncMock."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from equipment_manager.domain.demo import sample_payloads
from equipment_manager.domain.dto import DevicePayload
from equipment_manager.domain.exceptions import InventorySyncError
from equipment_manager.domain.models import Computer, InventoryRegistry
from equipment_manager.domain.sync import InventorySyncService, SyncResult

pytestmark = pytest.mark.asyncio


@pytest.fixture
def provider() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def payloads() -> list[DevicePayload]:
    return sample_payloads()


async def test_sync_adds_all_devices(
    provider: AsyncMock, registry: InventoryRegistry, payloads: list[DevicePayload]
) -> None:
    provider.fetch_devices.return_value = payloads

    result = await InventorySyncService(provider, registry).sync()

    assert result == SyncResult(added=3, duplicates=0, rejected=0)
    assert len(registry) == 3
    provider.fetch_devices.assert_awaited_once_with()


async def test_sync_skips_existing_devices(
    provider: AsyncMock,
    registry: InventoryRegistry,
    payloads: list[DevicePayload],
    device_factory: object,
) -> None:
    provider.fetch_devices.return_value = payloads
    service = InventorySyncService(provider, registry)
    await service.sync()

    again = await service.sync()

    assert again == SyncResult(added=0, duplicates=3, rejected=0)
    assert len(registry) == 3
    assert provider.fetch_devices.await_count == 2


async def test_invalid_payload_is_rejected_but_others_are_added(
    provider: AsyncMock, registry: InventoryRegistry, payloads: list[DevicePayload]
) -> None:
    broken = {**payloads[0], "inventory_number": "bad number"}
    provider.fetch_devices.return_value = [broken, payloads[1]]

    result = await InventorySyncService(provider, registry).sync()

    assert result == SyncResult(added=1, duplicates=0, rejected=1)
    assert "PC-009" in registry


async def test_empty_provider_answer(
    provider: AsyncMock, registry: InventoryRegistry
) -> None:
    provider.fetch_devices.return_value = []

    result = await InventorySyncService(provider, registry).sync()

    assert result == SyncResult(0, 0, 0)
    assert len(registry) == 0


@pytest.mark.parametrize(
    "error",
    [
        ConnectionError("Network error"),
        TimeoutError("Slow"),
        OSError("Disk"),
    ],
    ids=["connection", "timeout", "os"],
)
async def test_provider_failure_is_reported_and_registry_untouched(
    provider: AsyncMock, registry: InventoryRegistry, error: Exception
) -> None:
    provider.fetch_devices.side_effect = error

    with pytest.raises(InventorySyncError, match="provider failed") as exc_info:
        await InventorySyncService(provider, registry).sync()

    assert exc_info.value.__cause__ is error
    assert len(registry) == 0
    provider.fetch_devices.assert_awaited_once()


async def test_slow_provider_hits_the_timeout(
    provider: AsyncMock, registry: InventoryRegistry
) -> None:
    async def slow() -> list[DevicePayload]:
        await asyncio.sleep(1)
        return []

    provider.fetch_devices.side_effect = slow

    with pytest.raises(InventorySyncError) as exc_info:
        await InventorySyncService(provider, registry).sync(timeout=0.01)

    assert isinstance(exc_info.value.__cause__, TimeoutError)


async def test_synced_devices_have_the_expected_types(
    provider: AsyncMock, registry: InventoryRegistry, payloads: list[DevicePayload]
) -> None:
    provider.fetch_devices.return_value = payloads

    await InventorySyncService(provider, registry).sync()

    assert len(registry.by_type(Computer)) == 1
    assert registry["PC-002"].manufacturer.name == "Dell"


async def test_unexpected_error_is_not_swallowed(
    provider: AsyncMock, registry: InventoryRegistry
) -> None:
    provider.fetch_devices.side_effect = ZeroDivisionError

    with pytest.raises(ZeroDivisionError):
        await InventorySyncService(provider, registry).sync()
