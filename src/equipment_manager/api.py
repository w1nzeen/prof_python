"""FastAPI application for the computer equipment manager."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from sqlalchemy.orm import Session, sessionmaker

from equipment_manager.exceptions import (
    DuplicateDeviceError,
    EquipmentError,
    InvalidDeviceError,
)
from equipment_manager.external_api import fetch_devices
from equipment_manager.models import Device
from equipment_manager.persistence.database import (
    create_db_engine,
    create_session_factory,
)
from equipment_manager.persistence.exceptions import RecordNotFoundError
from equipment_manager.persistence.models import DeviceModel
from equipment_manager.persistence.services import EquipmentService
from equipment_manager.schemas import (
    DeviceBatchRequest,
    DeviceCreate,
    DeviceResponse,
    DeviceUpdate,
    ManufacturerResponse,
    StatisticsResponse,
)

app = FastAPI(
    title="Equipment Manager API",
    version="0.8.0",
    description="REST API for the computer equipment accounting system.",
)

engine = create_db_engine()
SessionFactory = create_session_factory(engine)


def get_session() -> Iterator[Session]:
    """Provide one SQLAlchemy session per HTTP request."""
    with SessionFactory() as session:
        yield session


def get_service(session: Session = Depends(get_session)) -> EquipmentService:
    """Create a service bound to the current request session."""
    return EquipmentService(session)


def make_device_response(device: DeviceModel) -> DeviceResponse:
    """Convert an ORM model into an API response schema."""
    return DeviceResponse(
        id=device.id,
        inventory_number=device.inventory_number,
        device_type=device.device_type,
        manufacturer=device.manufacturer.name,
        model=device.model,
        cost=device.cost,
        location=device.location,
    )


def get_device_or_404(
    service: EquipmentService,
    device_id: int,
) -> DeviceModel:
    """Load a device or return the standard HTTP not-found error."""
    device = service.devices.get_by_id(device_id)

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found.",
        )

    return device


@app.get("/")
async def root() -> dict[str, str]:
    """Return the application health response."""
    return {"message": "Equipment Manager API is running"}


@app.get(
    "/devices/statistics",
    response_model=StatisticsResponse,
)
async def get_statistics(
    service: EquipmentService = Depends(get_service),
) -> StatisticsResponse:
    """Return SQL-based statistics for all equipment."""
    statistics = service.statistics()

    return StatisticsResponse(
        count=statistics.count,
        total_cost=statistics.total_cost,
        average_cost=statistics.average_cost,
        most_expensive=(
            make_device_response(statistics.most_expensive)
            if statistics.most_expensive is not None
            else None
        ),
        count_by_manufacturer=statistics.count_by_manufacturer,
    )


@app.get(
    "/devices",
    response_model=list[DeviceResponse],
)
async def list_devices(
    query: str | None = Query(default=None, max_length=100),
    manufacturer: str | None = Query(default=None, max_length=100),
    service: EquipmentService = Depends(get_service),
) -> list[DeviceResponse]:
    """List devices, search them or filter them by manufacturer."""
    if query and manufacturer:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Use either query or manufacturer, not both.",
        )

    if query:
        devices = service.search_devices(query)
    elif manufacturer:
        devices = service.filter_by_manufacturer(manufacturer)
    else:
        devices = service.list_devices()

    return [make_device_response(device) for device in devices]


@app.post(
    "/devices",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_device(
    data: DeviceCreate,
    service: EquipmentService = Depends(get_service),
) -> DeviceResponse:
    """Create one device and its manufacturer when necessary."""
    try:
        device = service.register_device(
            Device(
                inventory_number=data.inventory_number,
                device_type=data.device_type,
                manufacturer=data.manufacturer,
                model=data.model,
                cost=data.cost,
            ),
            location=data.location,
        )
    except DuplicateDeviceError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except InvalidDeviceError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except EquipmentError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return make_device_response(device)


@app.get(
    "/devices/{device_id}",
    response_model=DeviceResponse,
)
async def get_device(
    device_id: int,
    service: EquipmentService = Depends(get_service),
) -> DeviceResponse:
    """Return one device by its database ID."""
    return make_device_response(get_device_or_404(service, device_id))


@app.patch(
    "/devices/{device_id}",
    response_model=DeviceResponse,
)
async def update_device(
    device_id: int,
    data: DeviceUpdate,
    service: EquipmentService = Depends(get_service),
) -> DeviceResponse:
    """Partially update a device."""
    updates = data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one field must be provided.",
        )

    try:
        with service.transaction():
            device = get_device_or_404(service, device_id)

            if "manufacturer" in updates:
                manufacturer_name = str(updates["manufacturer"])
                manufacturer = service.manufacturers.get_by_name(manufacturer_name)

                if manufacturer is None:
                    manufacturer = service.manufacturers.add(manufacturer_name)

                device.manufacturer = manufacturer

            for field in ("device_type", "model", "cost", "location"):
                if field in updates:
                    setattr(device, field, updates[field])

            service.devices.update(device)
    except InvalidDeviceError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except EquipmentError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return make_device_response(device)


@app.delete(
    "/devices/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_device(
    device_id: int,
    service: EquipmentService = Depends(get_service),
) -> Response:
    """Delete a device by its database ID."""
    device = get_device_or_404(service, device_id)

    try:
        service.remove_device(device.inventory_number)
    except RecordNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get(
    "/manufacturers/{manufacturer_id}/devices",
    response_model=list[DeviceResponse],
)
async def get_manufacturer_devices(
    manufacturer_id: int,
    service: EquipmentService = Depends(get_service),
) -> list[DeviceResponse]:
    """Return all devices of one manufacturer."""
    manufacturer = service.manufacturers.get_by_id(manufacturer_id)

    if manufacturer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manufacturer not found.",
        )

    return [
        make_device_response(device)
        for device in service.filter_by_manufacturer(manufacturer.name)
    ]


@app.get(
    "/manufacturers",
    response_model=list[ManufacturerResponse],
)
async def list_manufacturers(
    service: EquipmentService = Depends(get_service),
) -> list[ManufacturerResponse]:
    """List all manufacturers."""
    return [
        ManufacturerResponse(id=manufacturer.id, name=manufacturer.name)
        for manufacturer in service.manufacturers.get_all()
    ]


@app.post(
    "/devices/batch-fetch",
    response_model=list[DeviceResponse],
)
async def batch_fetch_devices(
    data: DeviceBatchRequest,
    base_url: str = Query(default="http://127.0.0.1:8000"),
    timeout: float = Query(default=5.0, gt=0, le=30),
) -> list[DeviceResponse]:
    """Load multiple devices concurrently through HTTPX."""
    try:
        payloads = await fetch_devices(
            base_url,
            data.device_ids,
            timeout=timeout,
            max_concurrency=3,
        )
    except asyncio.TimeoutError as error:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Batch operation timed out.",
        ) from error
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"External HTTP request failed: {error}",
        ) from error

    return [DeviceResponse.model_validate(payload) for payload in payloads]