"""
Truck and Preferred Lanes API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.carrier import CarrierProfile
from app.models.truck import Truck, PreferredLane
from app.schemas.trucks import (
    TruckCreate, TruckUpdate, TruckResponse,
    PreferredLaneCreate, PreferredLaneResponse,
)

router = APIRouter(tags=["trucks"])


# --- Truck Endpoints ---

@router.post("/api/trucks", response_model=TruckResponse, status_code=201)
async def create_truck(data: TruckCreate, db: AsyncSession = Depends(get_db)):
    """Create a new truck. Must belong to an existing carrier."""
    # Verify carrier exists
    carrier = await db.execute(select(CarrierProfile).where(CarrierProfile.id == data.carrier_id))
    if not carrier.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="carrier_id does not exist")

    truck = Truck(**data.model_dump())
    db.add(truck)
    await db.commit()
    await db.refresh(truck)
    return truck


@router.get("/api/trucks/{truck_id}", response_model=TruckResponse)
async def get_truck(truck_id: int, db: AsyncSession = Depends(get_db)):
    """Get a truck by ID."""
    result = await db.execute(select(Truck).where(Truck.id == truck_id))
    truck = result.scalar_one_or_none()
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")
    return truck


@router.put("/api/trucks/{truck_id}", response_model=TruckResponse)
async def update_truck(truck_id: int, data: TruckUpdate, db: AsyncSession = Depends(get_db)):
    """Update a truck's details (especially current location)."""
    result = await db.execute(select(Truck).where(Truck.id == truck_id))
    truck = result.scalar_one_or_none()
    if not truck:
        raise HTTPException(status_code=404, detail="Truck not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(truck, field, value)

    await db.commit()
    await db.refresh(truck)
    return truck


@router.get("/api/trucks", response_model=list[TruckResponse])
async def list_trucks(carrier_id: int = Query(...), db: AsyncSession = Depends(get_db)):
    """List all trucks for a carrier."""
    result = await db.execute(select(Truck).where(Truck.carrier_id == carrier_id))
    return result.scalars().all()


# --- Preferred Lane Endpoints ---

@router.post("/api/trucks/{truck_id}/lanes", response_model=PreferredLaneResponse, status_code=201)
async def create_lane(truck_id: int, data: PreferredLaneCreate, db: AsyncSession = Depends(get_db)):
    """Add a preferred lane to a truck."""
    result = await db.execute(select(Truck).where(Truck.id == truck_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Truck not found")

    lane = PreferredLane(truck_id=truck_id, **data.model_dump())
    db.add(lane)
    await db.commit()
    await db.refresh(lane)
    return lane


@router.get("/api/trucks/{truck_id}/lanes", response_model=list[PreferredLaneResponse])
async def list_lanes(truck_id: int, db: AsyncSession = Depends(get_db)):
    """List all preferred lanes for a truck."""
    result = await db.execute(select(PreferredLane).where(PreferredLane.truck_id == truck_id))
    return result.scalars().all()


@router.delete("/api/trucks/{truck_id}/lanes/{lane_id}", status_code=204)
async def delete_lane(truck_id: int, lane_id: int, db: AsyncSession = Depends(get_db)):
    """Remove a preferred lane."""
    result = await db.execute(
        select(PreferredLane).where(PreferredLane.id == lane_id, PreferredLane.truck_id == truck_id)
    )
    lane = result.scalar_one_or_none()
    if not lane:
        raise HTTPException(status_code=404, detail="Lane not found")

    await db.delete(lane)
    await db.commit()
