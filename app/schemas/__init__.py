"""
Pydantic schemas for CarrierProfile.

BEGINNER NOTE:
- "Schemas" define what data looks like coming IN (from the user) and going OUT (to the user)
- They validate input automatically — if someone sends mc_number="abc", it'll reject it
- They're separate from the database model so you control exactly what's exposed
"""

import re
from datetime import date, datetime

from pydantic import BaseModel, field_validator


class CarrierProfileCreate(BaseModel):
    """What the user sends when creating a carrier profile."""

    company_name: str
    mc_number: str
    dot_number: str
    insurance_provider: str | None = None
    insurance_policy_number: str | None = None
    insurance_expiry: date | None = None
    contact_name: str
    contact_email: str
    contact_phone: str

    @field_validator("mc_number")
    @classmethod
    def validate_mc_number(cls, v: str) -> str:
        """MC number must be exactly 6 digits."""
        if not re.match(r"^\d{6}$", v):
            raise ValueError("mc_number must be exactly 6 digits (e.g. '123456')")
        return v

    @field_validator("dot_number")
    @classmethod
    def validate_dot_number(cls, v: str) -> str:
        """DOT number must be 7 or 8 digits."""
        if not re.match(r"^\d{7,8}$", v):
            raise ValueError("dot_number must be 7 or 8 digits (e.g. '1234567')")
        return v


class CarrierProfileUpdate(BaseModel):
    """What the user sends when updating — all fields optional."""

    company_name: str | None = None
    mc_number: str | None = None
    dot_number: str | None = None
    insurance_provider: str | None = None
    insurance_policy_number: str | None = None
    insurance_expiry: date | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None

    @field_validator("mc_number")
    @classmethod
    def validate_mc_number(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^\d{6}$", v):
            raise ValueError("mc_number must be exactly 6 digits")
        return v

    @field_validator("dot_number")
    @classmethod
    def validate_dot_number(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^\d{7,8}$", v):
            raise ValueError("dot_number must be 7 or 8 digits")
        return v


class CarrierProfileResponse(BaseModel):
    """What the API sends back to the user."""

    id: int
    company_name: str
    mc_number: str
    dot_number: str
    insurance_provider: str | None
    insurance_policy_number: str | None
    insurance_expiry: date | None
    contact_name: str
    contact_email: str
    contact_phone: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
