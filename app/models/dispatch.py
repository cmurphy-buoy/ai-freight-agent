import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DispatchStatus(str, enum.Enum):
    assigned = "assigned"
    en_route_pickup = "en_route_pickup"
    at_pickup = "at_pickup"
    loaded = "loaded"
    en_route_delivery = "en_route_delivery"
    at_delivery = "at_delivery"
    delivered = "delivered"
    cancelled = "cancelled"


class Dispatch(Base):
    __tablename__ = "dispatches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), unique=True, nullable=False)
    truck_id: Mapped[int] = mapped_column(ForeignKey("trucks.id"), nullable=False)
    carrier_id: Mapped[int] = mapped_column(ForeignKey("carrier_profiles.id"), nullable=False)
    driver_name: Mapped[str] = mapped_column(String(200), nullable=False)
    driver_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[DispatchStatus] = mapped_column(Enum(DispatchStatus), nullable=False, default=DispatchStatus.assigned)
    pickup_confirmation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    delivery_confirmation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    invoice: Mapped["Invoice"] = relationship("Invoice")
    truck: Mapped["Truck"] = relationship("Truck")
    carrier: Mapped["CarrierProfile"] = relationship("CarrierProfile")
