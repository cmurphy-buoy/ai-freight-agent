import re
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank import BankConnection, BankTransaction
from app.models.invoice import Invoice, InvoiceStatus

STRIP_SUFFIXES = re.compile(
    r"\b(logistics|freight|inc|llc|corp|co|transportation|trucking|brokerage|services|group)\b",
    re.IGNORECASE,
)


def _normalize_name(name: str) -> str:
    name = name.lower().strip()
    name = STRIP_SUFFIXES.sub("", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


class ReconciliationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def reconcile(self, carrier_id: int) -> dict:
        # Get outstanding/sent/overdue invoices
        inv_result = await self.db.execute(
            select(Invoice).where(
                Invoice.carrier_id == carrier_id,
                Invoice.status.in_([
                    InvoiceStatus.outstanding,
                    InvoiceStatus.sent,
                    InvoiceStatus.overdue,
                ]),
            )
        )
        invoices = list(inv_result.scalars().all())

        # Get unreconciled deposits across active bank connections
        conn_result = await self.db.execute(
            select(BankConnection).where(
                BankConnection.carrier_id == carrier_id,
                BankConnection.is_active == True,
            )
        )
        connections = conn_result.scalars().all()
        conn_ids = [c.id for c in connections]

        if not conn_ids:
            return {
                "matched_count": 0,
                "unmatched_deposits": [],
                "newly_paid_invoices": [],
                "needs_review": [],
            }

        txn_result = await self.db.execute(
            select(BankTransaction).where(
                BankTransaction.bank_connection_id.in_(conn_ids),
                BankTransaction.is_deposit == True,
                BankTransaction.is_reconciled == False,
            ).order_by(BankTransaction.date.asc())
        )
        deposits = list(txn_result.scalars().all())

        matched_count = 0
        newly_paid = []
        unmatched = []
        needs_review = []
        matched_invoice_ids = set()

        for deposit in deposits:
            desc_lower = deposit.description.lower()
            deposit_amount = float(deposit.amount)
            candidates = []

            for inv in invoices:
                if inv.id in matched_invoice_ids:
                    continue

                # Amount check: within $0.50
                if abs(float(inv.amount) - deposit_amount) > 0.50:
                    continue

                # Name/MC check
                normalized_broker = _normalize_name(inv.broker_name)
                if normalized_broker in desc_lower or inv.broker_mc in desc_lower:
                    candidates.append(inv)

            if len(candidates) == 1:
                inv = candidates[0]
                inv.status = InvoiceStatus.paid
                inv.payment_date = deposit.date
                deposit.is_reconciled = True
                deposit.matched_invoice_id = inv.id
                matched_invoice_ids.add(inv.id)
                matched_count += 1
                newly_paid.append({
                    "id": inv.id,
                    "broker_name": inv.broker_name,
                    "amount": str(inv.amount),
                })
            elif len(candidates) > 1:
                needs_review.append({
                    "deposit": {
                        "id": deposit.id,
                        "date": str(deposit.date),
                        "description": deposit.description,
                        "amount": str(deposit.amount),
                    },
                    "possible_invoices": [
                        {"id": inv.id, "broker_name": inv.broker_name, "amount": str(inv.amount)}
                        for inv in candidates
                    ],
                })
            else:
                unmatched.append({
                    "id": deposit.id,
                    "date": str(deposit.date),
                    "description": deposit.description,
                    "amount": str(deposit.amount),
                })

        await self.db.commit()

        return {
            "matched_count": matched_count,
            "unmatched_deposits": unmatched,
            "newly_paid_invoices": newly_paid,
            "needs_review": needs_review,
        }
