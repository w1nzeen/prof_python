"""Pydantic schemas for the REST API."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeviceCreate(BaseModel):
    """Request body for creating a device."""

    inventory_number: str = Field(min_length=1, max_length=50)
    device_type: str = Field(min_length=1, max_length=50)
    manufacturer: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    cost: float = Field(ge=0)
    location: str | None = Field(default=None, max_length=100)

    @field_validator(
        "inventory_number",
        "device_type",
        "manufacturer",
        "model",
    )
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Value must not be empty.")

        return value

    @field_validator("location")
    @classmethod
    def strip_location(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None

    @field_validator("cost")
    @classmethod
    def validate_cost(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Cost must be a finite number.")

        return value


class DeviceUpdate(BaseModel):
    """Request body for partial device updates."""

    device_type: str | None = Field(default=None, min_length=1, max_length=50)
    manufacturer: str | None = Field(default=None, min_length=1, max_length=100)
    model: str | None = Field(default=None, min_length=1, max_length=100)
    cost: float | None = Field(default=None, ge=0)
    location: str | None = Field(default=None, max_length=100)

    @field_validator("device_type", "manufacturer", "model")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Value must not be empty.")

        return value

    @field_validator("location")
    @classmethod
    def strip_optional_location(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None

    @field_validator("cost")
    @classmethod
    def validate_optional_cost(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("Cost must be a finite number.")

        return value


class DeviceResponse(BaseModel):
    """JSON representation of a device."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    inventory_number: str
    device_type: str
    manufacturer: str
    model: str
    cost: float
    location: str | None


class ManufacturerResponse(BaseModel):
    """JSON representation of a manufacturer."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class StatisticsResponse(BaseModel):
    """Aggregated equipment statistics."""

    count: int
    total_cost: float
    average_cost: float
    most_expensive: DeviceResponse | None
    count_by_manufacturer: dict[str, int]


class DeviceBatchRequest(BaseModel):
    """Request body for parallel HTTP loading of devices."""

    device_ids: list[int] = Field(min_length=1, max_length=20)

    @field_validator("device_ids")
    @classmethod
    def validate_device_ids(cls, value: list[int]) -> list[int]:
        if any(device_id <= 0 for device_id in value):
            raise ValueError("Every device ID must be positive.")

        if len(value) != len(set(value)):
            raise ValueError("Device IDs must be unique.")

        return value