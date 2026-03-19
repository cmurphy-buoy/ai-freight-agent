"""
Profit/Loss report API routes.

Endpoints for generating P&L reports and monthly trend summaries.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.reports import ReportService

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/profit-loss")
async def get_profit_loss(
    carrier_id: int = Query(...),
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Get a profit/loss report for the given carrier and date range."""
    if not start_date:
        start_date = date.today().replace(day=1)
    if not end_date:
        end_date = date.today()
    service = ReportService(db)
    return await service.profit_loss(carrier_id, start_date, end_date)


@router.get("/monthly")
async def get_monthly_summary(
    carrier_id: int = Query(...),
    months: int = Query(default=6, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
):
    """Get monthly P&L summaries for the last N months."""
    service = ReportService(db)
    return await service.monthly_summary(carrier_id, months)
