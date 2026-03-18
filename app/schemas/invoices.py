from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.models.invoice import InvoiceStatus


class InvoiceCreate(BaseModel):
    carrier_id: int
    broker_name: str
    broker_mc: str
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    amount: Decimal
    rate_per_mile: Decimal
    miles: int
    invoice_date: date | None = None  # defaults to today in route
    due_date: date
    notes: str | None = None

    @field_validator("origin_state", "destination_state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        if len(v) != 2:
            raise ValueError("State must be 2-letter abbreviation")
        return v.upper()

    @field_validator("broker_mc")
    @classmethod
    def validate_mc(cls, v: str) -> str:
        if not v.isdigit() or len(v) > 6:
            raise ValueError("broker_mc must be up to 6 digits")
        return v


class InvoiceFromLoadCreate(BaseModel):
    carrier_id: int
    broker_name: str
    broker_mc: str
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    rate_total: Decimal  # maps to Invoice.amount
    rate_per_mile: Decimal
    miles: int
    load_reference: str | None = None


class InvoiceUpdate(BaseModel):
    status: InvoiceStatus | None = None
    payment_date: date | None = None
    payment_reference: str | None = None
    notes: str | None = None
    factoring_company: str | None = None
    due_date: date | None = None


class InvoiceResponse(BaseModel):
    id: int
    carrier_id: int
    load_reference: str | None
    broker_name: str
    broker_mc: str
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    amount: Decimal
    rate_per_mile: Decimal
    miles: int
    invoice_date: date
    due_date: date
    status: InvoiceStatus
    factoring_company: str | None
    payment_date: date | None
    payment_reference: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
