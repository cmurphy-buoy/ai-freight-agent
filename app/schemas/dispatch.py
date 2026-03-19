from datetime import datetime

from pydantic import BaseModel

from app.models.dispatch import DispatchStatus


class DispatchCreate(BaseModel):
    invoice_id: int
    truck_id: int
    carrier_id: int
    driver_name: str
    driver_phone: str | None = None
    notes: str | None = None


class DispatchUpdate(BaseModel):
    status: DispatchStatus | None = None
    driver_name: str | None = None
    driver_phone: str | None = None
    pickup_confirmation: str | None = None
    delivery_confirmation: str | None = None
    notes: str | None = None


class DispatchResponse(BaseModel):
    id: int
    invoice_id: int
    truck_id: int
    carrier_id: int
    driver_name: str
    driver_phone: str | None
    status: DispatchStatus
    pickup_confirmation: str | None
    delivery_confirmation: str | None
    notes: str | None
    assigned_at: datetime
    picked_up_at: datetime | None
    delivered_at: datetime | None
    updated_at: datetime

    model_config = {"from_attributes": True}
