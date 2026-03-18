from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.bank import ConnectionType


class PlaidLinkRequest(BaseModel):
    carrier_id: int


class BankConnectionResponse(BaseModel):
    id: int
    carrier_id: int
    institution_name: str
    account_name: str
    account_mask: str
    connection_type: ConnectionType
    is_active: bool
    last_synced_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BankTransactionResponse(BaseModel):
    id: int
    transaction_id: str
    date: date
    description: str
    amount: Decimal
    category: str | None
    is_deposit: bool
    is_reconciled: bool
    matched_invoice_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CSVUploadResponse(BaseModel):
    imported: int
    skipped: int
    total_rows: int


class ReconciliationResponse(BaseModel):
    matched_count: int
    unmatched_deposits: list[dict]
    newly_paid_invoices: list[dict]
    needs_review: list[dict]


class CategorizationResponse(BaseModel):
    categorized_count: int
    by_category: dict[str, int]
