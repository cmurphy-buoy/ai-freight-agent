"""
CarrierProfile model — stores your trucking company's identity.

This is the core "who are you" table. Your MC number, DOT number,
insurance info, and contact details all live here.

BEGINNER NOTE:
- Each "Column" becomes a column in your database table
- "String(100)" means text up to 100 characters
- "nullable=False" means this field is required (can't be blank)
- "default=func.now()" means it auto-fills with the current time
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CarrierProfile(Base):
    __tablename__ = "carrier_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    mc_number: Mapped[str] = mapped_column(String(6), nullable=False, unique=True)
    dot_number: Mapped[str] = mapped_column(String(8), nullable=False, unique=True)
    insurance_provider: Mapped[str | None] = mapped_column(String(200), nullable=True)
    insurance_policy_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    insurance_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    contact_name: Mapped[str] = mapped_column(String(150), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    api_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationship — one carrier can have many trucks (set up in US-003)
    # trucks = relationship("Truck", back_populates="carrier")
