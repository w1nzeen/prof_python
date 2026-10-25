"""Asynchronous HTTP client helpers for the equipment API."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx


async def get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    attempts: int = 3,
) -> dict[str, Any]:
    """Load JSON from a URL with retry and incremental backoff."""
    for attempt in range(1, attempts + 1):
        try:
            response = await client.get(url)

            if response.status_code >= 500:
                response.raise_for_status()

            response.raise_for_status()

            return dict(response.json())
        except httpx.HTTPStatusError as error:
            if error.response.status_code < 500 or attempt == attempts:
                raise
        except httpx.RequestError:
            if attempt == attempts:
                raise

        await asyncio.sleep(attempt)

    raise RuntimeError("Unexpected retry state.")


async def fetch_device(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    base_url: str,
    device_id: int,
) -> dict[str, Any]:
    """Load one device while respecting the concurrency limit."""
    async with semaphore:
        return await get_with_retry(
            client,
            f"{base_url.rstrip('/')}/devices/{device_id}",
        )


async def fetch_devices(
    base_url: str,
    device_ids: list[int],
    *,
    timeout: float = 5.0,
    max_concurrency: int = 3,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[dict[str, Any]]:
    """Load several devices concurrently using Task, gather and Semaphore."""
    semaphore = asyncio.Semaphore(max_concurrency)

    async with httpx.AsyncClient(
        timeout=timeout,
        transport=transport,
    ) as client:
        tasks = [
            asyncio.create_task(
                fetch_device(
                    client,
                    semaphore,
                    base_url,
                    device_id,
                )
            )
            for device_id in device_ids
        ]

        return list(
            await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=timeout,
            )
        )