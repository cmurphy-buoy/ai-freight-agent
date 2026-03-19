"""
Carrier profile API routes.

These are the endpoints for creating, reading, and updating carrier profiles.

BEGINNER NOTE:
- @router.post("/api/carriers") means "when someone sends a POST request to /api/carriers, run this function"
- "db: AsyncSession = Depends(get_db)" automatically gives each request a fresh database connection
- We return Pydantic schemas (not raw database objects) so the API output is clean and predictable
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.carrier import CarrierProfile
from app.schemas import CarrierProfileCreate, CarrierProfileResponse, CarrierProfileUpdate

router = APIRouter(prefix="/api/carriers", tags=["carriers"])


@router.post("", response_model=CarrierProfileResponse, status_code=201)
async def create_carrier(data: CarrierProfileCreate, db: AsyncSession = Depends(get_db)):
    """Create a new carrier profile."""
    carrier = CarrierProfile(**data.model_dump())
    db.add(carrier)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="A carrier with this MC or DOT number already exists")
    await db.refresh(carrier)
    return carrier


@router.get("/{carrier_id}", response_model=CarrierProfileResponse)
async def get_carrier(carrier_id: int, db: AsyncSession = Depends(get_db)):
    """Get a carrier profile by ID."""
    result = await db.execute(select(CarrierProfile).where(CarrierProfile.id == carrier_id))
    carrier = result.scalar_one_or_none()
    if not carrier:
        raise HTTPException(status_code=404, detail="Carrier not found")
    return carrier


@router.put("/{carrier_id}", response_model=CarrierProfileResponse)
async def update_carrier(carrier_id: int, data: CarrierProfileUpdate, db: AsyncSession = Depends(get_db)):
    """Update an existing carrier profile. Only sends fields you want to change."""
    result = await db.execute(select(CarrierProfile).where(CarrierProfile.id == carrier_id))
    carrier = result.scalar_one_or_none()
    if not carrier:
        raise HTTPException(status_code=404, detail="Carrier not found")

    # Only update fields that were actually sent (not None)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(carrier, field, value)

    await db.commit()
    await db.refresh(carrier)
    return carrier
