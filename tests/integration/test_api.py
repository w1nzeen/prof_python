"""Integration tests for the FastAPI equipment API."""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from equipment_manager.api import app, get_session
from equipment_manager.external_api import fetch_devices
from equipment_manager.persistence.database import (
    create_db_engine,
    create_session_factory,
    init_db,
    sqlite_url,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def api_client(tmp_path) -> Iterator[TestClient]:
    """Create an isolated database and override the API session dependency."""
    engine = create_db_engine(sqlite_url(tmp_path / "api_test.db"))
    init_db(engine)
    session_factory: sessionmaker[Session] = create_session_factory(engine)

    def override_get_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    engine.dispose()


def create_device(client: TestClient) -> dict[str, object]:
    """Create a reusable test device through the HTTP API."""
    response = client.post(
        "/devices",
        json={
            "inventory_number": "PC-100",
            "device_type": "Laptop",
            "manufacturer": "Acer",
            "model": "Swift 3",
            "cost": 25000.0,
            "location": "Room 5",
        },
    )

    assert response.status_code == 201

    return dict(response.json())


def test_root_returns_health_response(api_client: TestClient) -> None:
    response = api_client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Equipment Manager API is running",
    }


def test_create_read_and_list_device(api_client: TestClient) -> None:
    created = create_device(api_client)

    response = api_client.get(f"/devices/{created['id']}")

    assert response.status_code == 200
    assert response.json()["inventory_number"] == "PC-100"
    assert response.json()["manufacturer"] == "Acer"

    response = api_client.get("/devices", params={"manufacturer": "acer"})

    assert response.status_code == 200
    assert [item["inventory_number"] for item in response.json()] == ["PC-100"]


def test_patch_device_updates_cost_location_and_manufacturer(
    api_client: TestClient,
) -> None:
    created = create_device(api_client)

    response = api_client.patch(
        f"/devices/{created['id']}",
        json={
            "cost": 28000.0,
            "location": "Room 101",
            "manufacturer": "Acer Ukraine",
        },
    )

    assert response.status_code == 200
    assert response.json()["cost"] == 28000.0
    assert response.json()["location"] == "Room 101"
    assert response.json()["manufacturer"] == "Acer Ukraine"


def test_delete_device_returns_no_content(api_client: TestClient) -> None:
    created = create_device(api_client)

    response = api_client.delete(f"/devices/{created['id']}")

    assert response.status_code == 204
    assert response.content == b""

    response = api_client.get(f"/devices/{created['id']}")

    assert response.status_code == 404


def test_invalid_device_payload_returns_validation_error(
    api_client: TestClient,
) -> None:
    response = api_client.post(
        "/devices",
        json={
            "inventory_number": "PC-101",
            "device_type": "Laptop",
            "manufacturer": "Acer",
            "model": "Swift",
            "cost": -1,
        },
    )

    assert response.status_code == 422


def test_statistics_and_manufacturer_devices(api_client: TestClient) -> None:
    first = create_device(api_client)

    second_response = api_client.post(
        "/devices",
        json={
            "inventory_number": "PC-102",
            "device_type": "Monitor",
            "manufacturer": "Acer",
            "model": "Vero",
            "cost": 8000.0,
        },
    )

    assert second_response.status_code == 201

    response = api_client.get("/devices/statistics")

    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert response.json()["total_cost"] == 33000.0
    assert response.json()["most_expensive"]["id"] == first["id"]

    manufacturers = api_client.get("/manufacturers").json()
    manufacturer_id = manufacturers[0]["id"]

    response = api_client.get(f"/manufacturers/{manufacturer_id}/devices")

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_async_httpx_client_uses_tasks_gather_and_semaphore() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        device_id = int(request.url.path.rsplit("/", maxsplit=1)[1])

        return httpx.Response(
            200,
            json={
                "id": device_id,
                "inventory_number": f"PC-{device_id}",
                "device_type": "Laptop",
                "manufacturer": "Acer",
                "model": "Swift",
                "cost": 1000.0,
                "location": None,
            },
        )

    transport = httpx.MockTransport(handler)

    devices = await fetch_devices(
        "http://testserver",
        [1, 2, 3],
        timeout=1.0,
        max_concurrency=2,
        transport=transport,
    )

    assert [device["id"] for device in devices] == [1, 2, 3]