import enum
from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class BidStatus(str, enum.Enum):
    pending = "pending"
    submitted = "submitted"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"
    withdrawn = "withdrawn"


class Bid(Base):
    __tablename__ = "bids"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey("carrier_profiles.id"), nullable=False)
    load_id: Mapped[str] = mapped_column(String(50), nullable=False)
    broker_name: Mapped[str] = mapped_column(String(200), nullable=False)
    broker_mc: Mapped[str] = mapped_column(String(6), nullable=False)
    origin_city: Mapped[str] = mapped_column(String(100), nullable=False)
    origin_state: Mapped[str] = mapped_column(String(2), nullable=False)
    destination_city: Mapped[str] = mapped_column(String(100), nullable=False)
    destination_state: Mapped[str] = mapped_column(String(2), nullable=False)
    miles: Mapped[int] = mapped_column(Integer, nullable=False)
    listed_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    bid_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    bid_rate_per_mile: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    status: Mapped[BidStatus] = mapped_column(Enum(BidStatus), default=BidStatus.pending)
    auto_bid: Mapped[bool] = mapped_column(default=False)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    carrier: Mapped["CarrierProfile"] = relationship("CarrierProfile")
