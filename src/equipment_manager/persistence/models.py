"""SQLAlchemy ORM models: manufacturers (1) -> devices (N)."""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

from equipment_manager.models import Device

# Explicit constraint names keep Alembic migrations stable (also in SQLite).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# SQLite: NOCASE makes "PC-001" and "pc-001" the same value for = and UNIQUE,
# exactly like the case-insensitive search of laboratory work 1.
CASE_INSENSITIVE = "NOCASE"


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class ManufacturerModel(Base):
    """Table `manufacturers` (the "one" side of the relationship)."""

    __tablename__ = "manufacturers"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        String(100, collation=CASE_INSENSITIVE),
        unique=True,
        nullable=False,
    )
    devices: Mapped[list[DeviceModel]] = relationship(
        back_populates="manufacturer",
    )

    def __repr__(self) -> str:
        return f"ManufacturerModel(id={self.id!r}, name={self.name!r})"


class DeviceModel(Base):
    """Table `devices` (the "many" side, FOREIGN KEY to manufacturers)."""

    __tablename__ = "devices"
    __table_args__ = (
        CheckConstraint("cost >= 0", name="cost_non_negative"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    inventory_number: Mapped[str] = mapped_column(
        String(50, collation=CASE_INSENSITIVE),
        unique=True,
        nullable=False,
    )
    device_type: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    cost: Mapped[float] = mapped_column(Float, nullable=False)
    manufacturer_id: Mapped[int] = mapped_column(
        ForeignKey("manufacturers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Added by the Alembic migration "add device location".
    location: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    manufacturer: Mapped[ManufacturerModel] = relationship(
        back_populates="devices",
    )

    @property
    def full_name(self) -> str:
        return f"{self.manufacturer.name} {self.model}"

    def to_device(self) -> Device:
        """Convert the row to the dataclass of laboratory work 1."""
        return Device(
            inventory_number=self.inventory_number,
            device_type=self.device_type,
            manufacturer=self.manufacturer.name,
            model=self.model,
            cost=self.cost,
        )

    def __repr__(self) -> str:
        return (
            f"DeviceModel(id={self.id!r}, "
            f"inventory_number={self.inventory_number!r})"
        )
