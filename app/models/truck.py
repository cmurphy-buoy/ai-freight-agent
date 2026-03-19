"""
Truck model — stores your truck's capabilities and current location.

This is what the system uses to filter loads:
- equipment_type: what kind of trailer (dry van, reefer, etc.)
- max_weight_lbs: heaviest load you can haul
- current location: where the truck is right now (for deadhead calculation)
- max_deadhead_miles: how far you'll drive empty to pick up a load
- min_rate_per_mile: your floor — won't show loads below this rate
"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EquipmentType(str, enum.Enum):
    """The types of trailers your truck can pull."""
    dry_van = "dry_van"
    reefer = "reefer"
    flatbed = "flatbed"
    step_deck = "step_deck"
    power_only = "power_only"


class Truck(Base):
    __tablename__ = "trucks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey("carrier_profiles.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    equipment_type: Mapped[EquipmentType] = mapped_column(Enum(EquipmentType), nullable=False)
    max_weight_lbs: Mapped[int] = mapped_column(Integer, nullable=False, default=45000)
    current_city: Mapped[str] = mapped_column(String(100), nullable=False)
    current_state: Mapped[str] = mapped_column(String(2), nullable=False)
    current_lat: Mapped[float] = mapped_column(Float, nullable=False)
    current_lng: Mapped[float] = mapped_column(Float, nullable=False)
    max_deadhead_miles: Mapped[int] = mapped_column(Integer, nullable=False, default=150)
    min_rate_per_mile: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=2.00)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    carrier: Mapped["CarrierProfile"] = relationship("CarrierProfile")
    preferred_lanes: Mapped[list["PreferredLane"]] = relationship("PreferredLane", back_populates="truck", cascade="all, delete-orphan")


class PreferredLane(Base):
    __tablename__ = "preferred_lanes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    truck_id: Mapped[int] = mapped_column(ForeignKey("trucks.id"), nullable=False)
    origin_city: Mapped[str] = mapped_column(String(100), nullable=False)
    origin_state: Mapped[str] = mapped_column(String(2), nullable=False)
    destination_city: Mapped[str] = mapped_column(String(100), nullable=False)
    destination_state: Mapped[str] = mapped_column(String(2), nullable=False)
    priority_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    truck: Mapped["Truck"] = relationship("Truck", back_populates="preferred_lanes")
