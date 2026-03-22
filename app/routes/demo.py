"""
Demo data seeding endpoint.

Creates a sample carrier with 3 trucks in different locations so the
Search Loads tab shows many results out of the box.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import generate_api_token
from app.db.database import get_db
from app.models.carrier import CarrierProfile
from app.models.truck import Truck, EquipmentType, PreferredLane

router = APIRouter(prefix="/api/demo", tags=["demo"])

DEMO_CARRIER = {
    "company_name": "Demo Trucking LLC",
    "mc_number": "999001",
    "dot_number": "9990011",
    "contact_name": "Demo Driver",
    "contact_email": "demo@example.com",
    "contact_phone": "555-000-0001",
}

DEMO_TRUCKS = [
    {
        "name": "Truck 1 — Dry Van (Atlanta)",
        "equipment_type": EquipmentType.dry_van,
        "max_weight_lbs": 45000,
        "current_city": "Atlanta",
        "current_state": "GA",
        "current_lat": 33.749,
        "current_lng": -84.388,
        "max_deadhead_miles": 500,
        "min_rate_per_mile": 1.80,
    },
    {
        "name": "Truck 2 — Reefer (Dallas)",
        "equipment_type": EquipmentType.reefer,
        "max_weight_lbs": 42000,
        "current_city": "Dallas",
        "current_state": "TX",
        "current_lat": 32.776,
        "current_lng": -96.797,
        "max_deadhead_miles": 500,
        "min_rate_per_mile": 2.00,
    },
    {
        "name": "Truck 3 — Flatbed (Nashville)",
        "equipment_type": EquipmentType.flatbed,
        "max_weight_lbs": 48000,
        "current_city": "Nashville",
        "current_state": "TN",
        "current_lat": 36.162,
        "current_lng": -86.781,
        "max_deadhead_miles": 500,
        "min_rate_per_mile": 2.20,
    },
]

DEMO_LANES = [
    # Truck 1 lanes (Atlanta)
    {"truck_index": 0, "origin_city": "Atlanta", "origin_state": "GA", "destination_city": "Jacksonville", "destination_state": "FL", "priority_weight": 8},
    {"truck_index": 0, "origin_city": "Atlanta", "origin_state": "GA", "destination_city": "Charlotte", "destination_state": "NC", "priority_weight": 7},
    # Truck 2 lanes (Dallas)
    {"truck_index": 1, "origin_city": "Dallas", "origin_state": "TX", "destination_city": "Houston", "destination_state": "TX", "priority_weight": 9},
    {"truck_index": 1, "origin_city": "Dallas", "origin_state": "TX", "destination_city": "San Antonio", "destination_state": "TX", "priority_weight": 6},
    # Truck 3 lanes (Nashville)
    {"truck_index": 2, "origin_city": "Nashville", "origin_state": "TN", "destination_city": "Atlanta", "destination_state": "GA", "priority_weight": 8},
    {"truck_index": 2, "origin_city": "Nashville", "origin_state": "TN", "destination_city": "Memphis", "destination_state": "TN", "priority_weight": 7},
]


@router.post("/seed")
async def seed_demo_data(db: AsyncSession = Depends(get_db)):
    """
    Create a demo carrier with 3 trucks and preferred lanes.
    Returns the carrier ID so the frontend can use it immediately.
    Idempotent — skips if demo carrier already exists.
    """
    # Check if demo carrier already exists
    result = await db.execute(
        select(CarrierProfile).where(CarrierProfile.mc_number == "999001")
    )
    existing = result.scalar_one_or_none()
    if existing:
        # Return existing carrier with its trucks
        truck_result = await db.execute(
            select(Truck).where(Truck.carrier_id == existing.id)
        )
        trucks = list(truck_result.scalars().all())
        return {
            "message": "Demo data already exists",
            "carrier_id": existing.id,
            "carrier_name": existing.company_name,
            "trucks": [{"id": t.id, "name": t.name, "equipment_type": t.equipment_type.value} for t in trucks],
        }

    # Create carrier
    carrier = CarrierProfile(**DEMO_CARRIER)
    carrier.api_token = generate_api_token()
    db.add(carrier)
    await db.flush()  # Get the carrier ID

    # Create trucks
    created_trucks = []
    for truck_data in DEMO_TRUCKS:
        truck = Truck(carrier_id=carrier.id, **truck_data)
        db.add(truck)
        created_trucks.append(truck)

    await db.flush()  # Get truck IDs

    # Create preferred lanes
    for lane_data in DEMO_LANES:
        truck_index = lane_data.pop("truck_index")
        lane = PreferredLane(truck_id=created_trucks[truck_index].id, **lane_data)
        db.add(lane)

    await db.commit()

    return {
        "message": "Demo data created successfully",
        "carrier_id": carrier.id,
        "carrier_name": carrier.company_name,
        "trucks": [{"id": t.id, "name": t.name, "equipment_type": t.equipment_type.value} for t in created_trucks],
    }
