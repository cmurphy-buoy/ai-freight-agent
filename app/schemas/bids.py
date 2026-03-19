from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
from app.models.bid import BidStatus


class BidCreate(BaseModel):
    carrier_id: int
    load_id: str
    broker_name: str
    broker_mc: str
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    miles: int
    listed_rate: Decimal
    bid_amount: Decimal
    bid_rate_per_mile: Decimal
    auto_bid: bool = False
    score: int | None = None
    notes: str | None = None


class BidUpdate(BaseModel):
    status: BidStatus | None = None
    bid_amount: Decimal | None = None
    bid_rate_per_mile: Decimal | None = None
    notes: str | None = None


class BidResponse(BaseModel):
    id: int
    carrier_id: int
    load_id: str
    broker_name: str
    broker_mc: str
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    miles: int
    listed_rate: Decimal
    bid_amount: Decimal
    bid_rate_per_mile: Decimal
    status: BidStatus
    auto_bid: bool
    score: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AutoBidConfig(BaseModel):
    min_score: int = 70
    bid_strategy: str = "market"  # "market", "aggressive", "conservative"
    max_bids_per_search: int = 3
