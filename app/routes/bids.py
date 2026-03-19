from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.models.bid import Bid, BidStatus
from app.schemas.bids import BidCreate, BidUpdate, BidResponse, AutoBidConfig
from app.services.bidding import BiddingService

router = APIRouter(prefix="/api/bids", tags=["bids"])


@router.post("", response_model=BidResponse, status_code=201)
async def create_bid(data: BidCreate, db: AsyncSession = Depends(get_db)):
    bid = Bid(**data.model_dump())
    bid.status = BidStatus.submitted
    db.add(bid)
    await db.commit()
    await db.refresh(bid)
    return bid


@router.get("/{bid_id}", response_model=BidResponse)
async def get_bid(bid_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bid).where(Bid.id == bid_id))
    bid = result.scalar_one_or_none()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    return bid


@router.put("/{bid_id}", response_model=BidResponse)
async def update_bid(bid_id: int, data: BidUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bid).where(Bid.id == bid_id))
    bid = result.scalar_one_or_none()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(bid, field, value)
    await db.commit()
    await db.refresh(bid)
    return bid


@router.get("", response_model=list[BidResponse])
async def list_bids(
    carrier_id: int = Query(...),
    status: BidStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Bid).where(Bid.carrier_id == carrier_id)
    if status:
        query = query.where(Bid.status == status)
    query = query.order_by(Bid.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/auto-bid")
async def auto_bid(
    carrier_id: int = Query(...),
    truck_id: int = Query(...),
    config: AutoBidConfig = None,
    db: AsyncSession = Depends(get_db),
):
    """Run auto-bidding: search loads for truck, score them, bid on top matches."""
    from app.models.truck import Truck
    from app.services.mock_dat import MockDATService
    from app.services.scoring import LoadScoringService

    if config is None:
        config = AutoBidConfig()

    # Get truck
    truck_result = await db.execute(select(Truck).where(Truck.id == truck_id))
    truck = truck_result.scalar_one_or_none()
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")

    # Search and score loads
    from app.services.mock_truckstop import MockTruckstopService
    dat = MockDATService()
    ts = MockTruckstopService()
    dat_loads = dat.search_loads(truck.equipment_type.value, truck.current_lat, truck.current_lng, truck.max_deadhead_miles)
    ts_loads = ts.search_loads(truck.equipment_type.value, truck.current_lat, truck.current_lng, truck.max_deadhead_miles)
    raw_loads = dat_loads + ts_loads

    # Filter overweight loads
    filtered = [load for load in raw_loads if load["weight_lbs"] <= truck.max_weight_lbs or load["weight_lbs"] == 0]

    # Get preferred lanes for scoring
    from app.models.truck import PreferredLane
    lanes_result = await db.execute(select(PreferredLane).where(PreferredLane.truck_id == truck_id))
    lanes = lanes_result.scalars().all()
    lane_dicts = [{"origin_city": l.origin_city, "origin_state": l.origin_state, "destination_city": l.destination_city, "destination_state": l.destination_state, "priority_weight": l.priority_weight} for l in lanes]

    scorer = LoadScoringService(
        min_rate=truck.min_rate_per_mile,
        max_deadhead=truck.max_deadhead_miles,
        preferred_lanes=lane_dicts,
    )
    scored = scorer.score_loads(filtered)

    # Calculate bids
    bidding = BiddingService()
    auto_bids = bidding.auto_bid_loads(scored, config.min_score, config.bid_strategy, config.max_bids_per_search)

    # Save bids to DB
    created_bids = []
    for ab in auto_bids:
        bid = Bid(
            carrier_id=carrier_id,
            load_id=ab["load_id"],
            broker_name=ab["broker_name"],
            broker_mc=ab["broker_mc"],
            origin_city=ab["origin_city"],
            origin_state=ab["origin_state"],
            destination_city=ab["destination_city"],
            destination_state=ab["destination_state"],
            miles=ab["miles"],
            listed_rate=ab["rate_total"],
            bid_amount=ab["bid_amount"],
            bid_rate_per_mile=ab["bid_rate_per_mile"],
            status=BidStatus.submitted,
            auto_bid=True,
            score=ab["score"],
        )
        db.add(bid)
        created_bids.append(bid)

    await db.commit()
    for b in created_bids:
        await db.refresh(b)

    return {
        "loads_searched": len(raw_loads),
        "loads_scored": len(scored),
        "qualifying_loads": len([l for l in scored if l["score"] >= config.min_score]),
        "bids_placed": len(created_bids),
        "bids": [BidResponse.model_validate(b) for b in created_bids],
    }
