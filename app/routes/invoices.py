from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.carrier import CarrierProfile
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.invoices import (
    InvoiceCreate, InvoiceFromLoadCreate, InvoiceUpdate, InvoiceResponse,
)

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.post("", response_model=InvoiceResponse, status_code=201)
async def create_invoice(data: InvoiceCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CarrierProfile).where(CarrierProfile.id == data.carrier_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="carrier_id does not exist")

    invoice_data = data.model_dump()
    if invoice_data["invoice_date"] is None:
        invoice_data["invoice_date"] = date.today()

    invoice = Invoice(**invoice_data)
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return invoice


@router.post("/from-load", response_model=InvoiceResponse, status_code=201)
async def create_invoice_from_load(data: InvoiceFromLoadCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CarrierProfile).where(CarrierProfile.id == data.carrier_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="carrier_id does not exist")

    invoice = Invoice(
        carrier_id=data.carrier_id,
        broker_name=data.broker_name,
        broker_mc=data.broker_mc,
        origin_city=data.origin_city,
        origin_state=data.origin_state,
        destination_city=data.destination_city,
        destination_state=data.destination_state,
        amount=data.rate_total,
        rate_per_mile=data.rate_per_mile,
        miles=data.miles,
        load_reference=data.load_reference,
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=InvoiceStatus.draft,
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return invoice


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(invoice_id: int, data: InvoiceUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(invoice, field, value)

    await db.commit()
    await db.refresh(invoice)
    return invoice


@router.get("", response_model=list[InvoiceResponse])
async def list_invoices(
    carrier_id: int = Query(...),
    status: InvoiceStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Invoice).where(Invoice.carrier_id == carrier_id)
    if status:
        query = query.where(Invoice.status == status)
    result = await db.execute(query)
    return result.scalars().all()
