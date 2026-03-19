"""
Pydantic schemas for Trucks and Preferred Lanes.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.models.truck import EquipmentType


# --- Truck Schemas ---

class TruckCreate(BaseModel):
    carrier_id: int
    name: str
    equipment_type: EquipmentType
    max_weight_lbs: int = 45000
    current_city: str
    current_state: str
    current_lat: float
    current_lng: float
    max_deadhead_miles: int = 150
    min_rate_per_mile: Decimal = Decimal("2.00")

    @field_validator("current_state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        if len(v) != 2:
            raise ValueError("State must be 2-letter abbreviation (e.g. 'GA')")
        return v.upper()


class TruckUpdate(BaseModel):
    name: str | None = None
    equipment_type: EquipmentType | None = None
    max_weight_lbs: int | None = None
    current_city: str | None = None
    current_state: str | None = None
    current_lat: float | None = None
    current_lng: float | None = None
    max_deadhead_miles: int | None = None
    min_rate_per_mile: Decimal | None = None


class TruckResponse(BaseModel):
    id: int
    carrier_id: int
    name: str
    equipment_type: EquipmentType
    max_weight_lbs: int
    current_city: str
    current_state: str
    current_lat: float
    current_lng: float
    max_deadhead_miles: int
    min_rate_per_mile: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Preferred Lane Schemas ---

class PreferredLaneCreate(BaseModel):
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    priority_weight: int = 5

    @field_validator("priority_weight")
    @classmethod
    def validate_weight(cls, v: int) -> int:
        if not 1 <= v <= 10:
            raise ValueError("priority_weight must be between 1 and 10")
        return v


class PreferredLaneResponse(BaseModel):
    id: int
    truck_id: int
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    priority_weight: int
    created_at: datetime

    model_config = {"from_attributes": True}
