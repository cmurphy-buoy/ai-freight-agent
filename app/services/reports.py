"""
Profit/Loss reporting service.

Aggregates revenue from paid/factored invoices and expenses from bank
transactions to produce P&L reports and monthly trend summaries.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice, InvoiceStatus
from app.models.bank import BankTransaction, BankConnection


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def profit_loss(self, carrier_id: int, start_date: date, end_date: date) -> dict:
        """Generate a profit/loss report for the given date range."""

        # Revenue: paid/factored invoices in date range
        rev_result = await self.db.execute(
            select(
                func.coalesce(func.sum(Invoice.amount), 0).label("total"),
                func.count(Invoice.id).label("count"),
            ).where(
                Invoice.carrier_id == carrier_id,
                Invoice.status.in_([InvoiceStatus.paid, InvoiceStatus.factored]),
                Invoice.payment_date >= start_date,
                Invoice.payment_date <= end_date,
            )
        )
        rev = rev_result.one()

        # Find active bank connections for this carrier
        conn_result = await self.db.execute(
            select(BankConnection.id).where(
                BankConnection.carrier_id == carrier_id,
                BankConnection.is_active == True,
            )
        )
        conn_ids = [r[0] for r in conn_result.all()]

        expenses_by_category: dict[str, dict] = {}
        total_expenses = Decimal("0")

        if conn_ids:
            exp_result = await self.db.execute(
                select(
                    func.coalesce(BankTransaction.category, "uncategorized").label("cat"),
                    func.sum(func.abs(BankTransaction.amount)).label("total"),
                    func.count(BankTransaction.id).label("count"),
                ).where(
                    BankTransaction.bank_connection_id.in_(conn_ids),
                    BankTransaction.is_deposit == False,
                    BankTransaction.date >= start_date,
                    BankTransaction.date <= end_date,
                ).group_by(BankTransaction.category)
            )
            for row in exp_result.all():
                cat_name = row.cat or "uncategorized"
                amt = float(row.total)
                expenses_by_category[cat_name] = {
                    "amount": round(amt, 2),
                    "count": row.count,
                }
                total_expenses += Decimal(str(amt))

        revenue = float(rev.total)
        expenses = float(total_expenses)
        net_profit = round(revenue - expenses, 2)

        # Outstanding receivables (not date-filtered — always current)
        out_result = await self.db.execute(
            select(
                func.coalesce(func.sum(Invoice.amount), 0),
                func.count(Invoice.id),
            ).where(
                Invoice.carrier_id == carrier_id,
                Invoice.status.in_([InvoiceStatus.outstanding, InvoiceStatus.sent, InvoiceStatus.overdue]),
            )
        )
        outstanding = out_result.one()

        return {
            "period": {"start": str(start_date), "end": str(end_date)},
            "revenue": {
                "total": round(revenue, 2),
                "invoice_count": rev.count,
            },
            "expenses": {
                "total": round(expenses, 2),
                "by_category": expenses_by_category,
            },
            "net_profit": net_profit,
            "profit_margin": round((net_profit / revenue * 100), 1) if revenue > 0 else 0,
            "outstanding_receivables": {
                "total": round(float(outstanding[0]), 2),
                "count": outstanding[1],
            },
        }

    async def monthly_summary(self, carrier_id: int, months: int = 6) -> list[dict]:
        """Generate monthly P&L summaries for the last N months."""
        summaries = []
        today = date.today()
        for i in range(months):
            # Walk back i months from the start of the current month
            month_start = date(today.year, today.month, 1)
            for _ in range(i):
                month_start = (month_start - timedelta(days=1)).replace(day=1)
            if month_start.month == 12:
                month_end = date(month_start.year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)

            report = await self.profit_loss(carrier_id, month_start, month_end)
            report["month"] = month_start.strftime("%Y-%m")
            report["month_label"] = month_start.strftime("%b %Y")
            summaries.append(report)

        return list(reversed(summaries))
