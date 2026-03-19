from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.dispatch import Dispatch, DispatchStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.truck import Truck
from app.schemas.dispatch import DispatchCreate, DispatchUpdate, DispatchResponse

router = APIRouter(prefix="/api/dispatches", tags=["dispatches"])


@router.post("", response_model=DispatchResponse, status_code=201)
async def create_dispatch(data: DispatchCreate, db: AsyncSession = Depends(get_db)):
    # Verify invoice exists
    inv = await db.execute(select(Invoice).where(Invoice.id == data.invoice_id))
    invoice = inv.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=400, detail="Invoice not found")

    # Check no existing dispatch for this invoice
    existing = await db.execute(select(Dispatch).where(Dispatch.invoice_id == data.invoice_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Invoice already dispatched")

    # Verify truck exists
    truck_result = await db.execute(select(Truck).where(Truck.id == data.truck_id))
    if not truck_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Truck not found")

    dispatch = Dispatch(**data.model_dump())
    db.add(dispatch)

    # Update invoice status to sent (dispatched implies sent to broker)
    if invoice.status == InvoiceStatus.draft:
        invoice.status = InvoiceStatus.sent

    await db.commit()
    await db.refresh(dispatch)
    return dispatch


@router.get("/{dispatch_id}", response_model=DispatchResponse)
async def get_dispatch(dispatch_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dispatch).where(Dispatch.id == dispatch_id))
    dispatch = result.scalar_one_or_none()
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")
    return dispatch


@router.put("/{dispatch_id}", response_model=DispatchResponse)
async def update_dispatch(dispatch_id: int, data: DispatchUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dispatch).where(Dispatch.id == dispatch_id))
    dispatch = result.scalar_one_or_none()
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    update_data = data.model_dump(exclude_unset=True)

    # Auto-set timestamps based on status transitions
    new_status = update_data.get("status")
    if new_status:
        if new_status == DispatchStatus.loaded and not dispatch.picked_up_at:
            dispatch.picked_up_at = datetime.utcnow()
        elif new_status == DispatchStatus.delivered and not dispatch.delivered_at:
            dispatch.delivered_at = datetime.utcnow()
            # Update invoice to outstanding when delivered
            inv = await db.execute(select(Invoice).where(Invoice.id == dispatch.invoice_id))
            invoice = inv.scalar_one_or_none()
            if invoice and invoice.status == InvoiceStatus.sent:
                invoice.status = InvoiceStatus.outstanding

    for field, value in update_data.items():
        setattr(dispatch, field, value)

    await db.commit()
    await db.refresh(dispatch)
    return dispatch


@router.get("", response_model=list[DispatchResponse])
async def list_dispatches(
    carrier_id: int = Query(...),
    status: DispatchStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Dispatch).where(Dispatch.carrier_id == carrier_id)
    if status:
        query = query.where(Dispatch.status == status)
    query = query.order_by(Dispatch.assigned_at.desc())
    result = await db.execute(query)
    return result.scalars().all()
