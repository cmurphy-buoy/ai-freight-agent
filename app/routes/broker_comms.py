from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.models.dispatch import Dispatch
from app.models.invoice import Invoice
from app.models.carrier import CarrierProfile
from app.services.broker_comms import BrokerCommsService

router = APIRouter(prefix="/api/comms", tags=["broker_comms"])

comms_service = BrokerCommsService()


@router.get("/check-call/{dispatch_id}")
async def generate_check_call(dispatch_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Dispatch).where(Dispatch.id == dispatch_id))
    dispatch = result.scalar_one_or_none()
    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    inv_result = await db.execute(select(Invoice).where(Invoice.id == dispatch.invoice_id))
    invoice = inv_result.scalar_one_or_none()

    carrier_result = await db.execute(select(CarrierProfile).where(CarrierProfile.id == dispatch.carrier_id))
    carrier = carrier_result.scalar_one_or_none()

    data = {
        "driver_name": dispatch.driver_name,
        "broker_name": invoice.broker_name if invoice else "",
        "origin_city": invoice.origin_city if invoice else "",
        "origin_state": invoice.origin_state if invoice else "",
        "destination_city": invoice.destination_city if invoice else "",
        "destination_state": invoice.destination_state if invoice else "",
        "status": dispatch.status.value,
        "load_ref": invoice.load_reference or f"INV-{invoice.id}" if invoice else "",
        "company_name": carrier.company_name if carrier else "",
    }
    return comms_service.generate_check_call(data)


@router.get("/rate-con-request")
async def generate_rate_con_request(
    load_id: str = Query(...),
    broker_name: str = Query(...),
    origin_city: str = Query(...),
    origin_state: str = Query(...),
    dest_city: str = Query(...),
    dest_state: str = Query(...),
    rate_total: float = Query(...),
    carrier_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    carrier_result = await db.execute(select(CarrierProfile).where(CarrierProfile.id == carrier_id))
    carrier = carrier_result.scalar_one_or_none()

    data = {
        "broker_name": broker_name,
        "origin_city": origin_city,
        "origin_state": origin_state,
        "destination_city": dest_city,
        "destination_state": dest_state,
        "rate_total": rate_total,
        "company_name": carrier.company_name if carrier else "",
        "carrier_mc": carrier.mc_number if carrier else "",
    }
    return comms_service.generate_rate_confirmation_request(data)


@router.get("/invoice-reminder/{invoice_id}")
async def generate_invoice_reminder(invoice_id: int, db: AsyncSession = Depends(get_db)):
    inv_result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = inv_result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    carrier_result = await db.execute(select(CarrierProfile).where(CarrierProfile.id == invoice.carrier_id))
    carrier = carrier_result.scalar_one_or_none()

    from datetime import date
    days_overdue = max(0, (date.today() - invoice.due_date).days) if invoice.due_date else 0

    data = {
        "broker_name": invoice.broker_name,
        "amount": float(invoice.amount),
        "due_date": str(invoice.due_date),
        "invoice_id": invoice.id,
        "company_name": carrier.company_name if carrier else "",
        "days_overdue": days_overdue,
    }
    return comms_service.generate_invoice_reminder(data)
