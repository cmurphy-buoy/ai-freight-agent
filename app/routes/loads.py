"""
Load search API route.

This is the main endpoint carriers use:
    GET /api/loads/search?truck_id=1

It reads your truck's parameters, searches mock loads, filters by weight,
scores them, and returns ranked results.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.models.truck import Truck, PreferredLane
from app.services.mock_dat import MockDATService
from app.services.mock_truckstop import MockTruckstopService
from app.services.scoring import LoadScoringService

router = APIRouter(tags=["loads"])

# Create one instance of each mock service (shared across requests)
# In production, swap with RealDATService / RealTruckstopService
dat_service = MockDATService(seed=42)
truckstop_service = MockTruckstopService(seed=99)


@router.get("/api/loads/search")
async def search_loads(
    truck_id: int = Query(..., description="ID of the truck to search for"),
    db: AsyncSession = Depends(get_db),
):
    """
    Search for loads matching a truck's parameters.

    1. Reads truck info from database
    2. Searches mock DAT board by equipment type + location radius
    3. Filters out overweight loads
    4. Scores and ranks results
    5. Returns sorted list (best loads first)
    """

    # Step 1: Get the truck and its preferred lanes
    result = await db.execute(
        select(Truck)
        .options(selectinload(Truck.preferred_lanes))
        .where(Truck.id == truck_id)
    )
    truck = result.scalar_one_or_none()

    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")

    # Step 2: Search both load boards and merge results
    dat_loads = dat_service.search_loads(
        equipment_type=truck.equipment_type.value,
        origin_lat=truck.current_lat,
        origin_lng=truck.current_lng,
        radius_miles=truck.max_deadhead_miles,
    )
    ts_loads = truckstop_service.search_loads(
        equipment_type=truck.equipment_type.value,
        origin_lat=truck.current_lat,
        origin_lng=truck.current_lng,
        radius_miles=truck.max_deadhead_miles,
    )
    raw_loads = dat_loads + ts_loads

    # Step 3: Filter out loads that are too heavy for this truck
    filtered = [
        load for load in raw_loads
        if load["weight_lbs"] <= truck.max_weight_lbs or load["weight_lbs"] == 0
    ]

    # Step 4: Score and rank
    lanes_data = [
        {
            "origin_city": lane.origin_city,
            "origin_state": lane.origin_state,
            "destination_city": lane.destination_city,
            "destination_state": lane.destination_state,
            "priority_weight": lane.priority_weight,
        }
        for lane in truck.preferred_lanes
    ]

    scorer = LoadScoringService(
        min_rate=truck.min_rate_per_mile,
        max_deadhead=truck.max_deadhead_miles,
        preferred_lanes=lanes_data,
    )

    scored_loads = scorer.score_loads(filtered)

    return {
        "truck_id": truck.id,
        "truck_name": truck.name,
        "total_results": len(scored_loads),
        "loads": scored_loads,
    }


@router.get("/api/loads/browse")
async def browse_loads(
    equipment_type: str | None = Query(None, description="Filter by equipment type"),
    origin_state: str | None = Query(None, description="Filter by origin state"),
    limit: int = Query(50, description="Max results to return"),
):
    """
    Browse all available loads from both boards without needing a truck.
    No scoring — just raw load data sorted by rate/mile descending.
    """
    all_loads = dat_service.get_all_loads() + truckstop_service.get_all_loads()

    if equipment_type:
        all_loads = [l for l in all_loads if l["equipment_type"] == equipment_type]
    if origin_state:
        all_loads = [l for l in all_loads if l["origin_state"] == origin_state.upper()]

    # Sort by rate_per_mile descending (best paying first)
    all_loads.sort(key=lambda l: l["rate_per_mile"], reverse=True)
    all_loads = all_loads[:limit]

    return {
        "total_results": len(all_loads),
        "loads": all_loads,
    }
