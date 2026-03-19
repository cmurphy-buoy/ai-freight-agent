import csv
import hashlib
import io
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.bank import BankConnection, BankTransaction, ConnectionType
from app.models.carrier import CarrierProfile
from app.schemas.bank import (
    BankConnectionResponse,
    BankTransactionResponse,
    CategorizationResponse,
    CSVUploadResponse,
    PlaidLinkRequest,
    ReconciliationResponse,
)
from app.services.categorization import TransactionCategorizationService
from app.services.mock_plaid import MockPlaidService
from app.services.reconciliation import ReconciliationService

router = APIRouter(prefix="/api", tags=["bank"])

plaid_service = MockPlaidService()


# ---------------------------------------------------------------------------
# Bank Connection endpoints
# ---------------------------------------------------------------------------


@router.post("/bank-connections/plaid/link", response_model=BankConnectionResponse, status_code=201)
async def plaid_link(data: PlaidLinkRequest, db: AsyncSession = Depends(get_db)):
    """Create a bank connection via (mock) Plaid link flow."""
    carrier_result = await db.execute(
        select(CarrierProfile).where(CarrierProfile.id == data.carrier_id)
    )
    if not carrier_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="carrier_id does not exist")

    link_data = plaid_service.create_link(data.carrier_id)

    connection = BankConnection(
        carrier_id=data.carrier_id,
        institution_name=link_data["institution_name"],
        account_name=link_data["account_name"],
        account_mask=link_data["account_mask"],
        connection_type=ConnectionType.plaid,
        plaid_access_token=link_data["access_token"],
        plaid_item_id=link_data["item_id"],
    )
    db.add(connection)
    await db.commit()
    await db.refresh(connection)
    return connection


@router.get("/bank-connections", response_model=list[BankConnectionResponse])
async def list_connections(
    carrier_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """List active bank connections for a carrier."""
    query = (
        select(BankConnection)
        .where(BankConnection.carrier_id == carrier_id)
        .where(BankConnection.is_active == True)  # noqa: E712
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/bank-connections/{connection_id}", status_code=204)
async def delete_connection(connection_id: int, db: AsyncSession = Depends(get_db)):
    """Soft-delete a bank connection (set is_active=False)."""
    result = await db.execute(
        select(BankConnection).where(BankConnection.id == connection_id)
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="Bank connection not found")

    connection.is_active = False
    await db.commit()


# ---------------------------------------------------------------------------
# Sync (Plaid pull)
# ---------------------------------------------------------------------------


@router.post("/bank-connections/{connection_id}/sync", response_model=list[BankTransactionResponse])
async def sync_transactions(connection_id: int, db: AsyncSession = Depends(get_db)):
    """Pull transactions from (mock) Plaid and store them, deduplicating by transaction_id."""
    result = await db.execute(
        select(BankConnection).where(BankConnection.id == connection_id)
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=404, detail="Bank connection not found")
    if not connection.plaid_access_token:
        raise HTTPException(status_code=400, detail="Connection has no Plaid access token")

    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    raw_txns = plaid_service.get_transactions(connection.plaid_access_token, start_date, end_date)

    # Fetch existing transaction_ids to deduplicate
    existing_result = await db.execute(
        select(BankTransaction.transaction_id).where(
            BankTransaction.bank_connection_id == connection_id
        )
    )
    existing_ids = set(existing_result.scalars().all())

    new_transactions = []
    for txn in raw_txns:
        if txn["transaction_id"] in existing_ids:
            continue

        amount = Decimal(str(txn["amount"]))
        bank_txn = BankTransaction(
            bank_connection_id=connection_id,
            transaction_id=txn["transaction_id"],
            date=date.fromisoformat(txn["date"]),
            description=txn["description"],
            amount=abs(amount),
            is_deposit=amount > 0,
            raw_data=txn,
        )
        db.add(bank_txn)
        new_transactions.append(bank_txn)

    connection.last_synced_at = datetime.utcnow()
    await db.commit()

    for txn in new_transactions:
        await db.refresh(txn)

    return new_transactions


# ---------------------------------------------------------------------------
# CSV Upload
# ---------------------------------------------------------------------------


def _find_column(headers: list[str], candidates: list[str]) -> str | None:
    """Find the first header that matches any candidate (case-insensitive)."""
    lower_headers = {h.strip().lower(): h for h in headers}
    for candidate in candidates:
        if candidate.lower() in lower_headers:
            return lower_headers[candidate.lower()]
    return None


def _parse_date(value: str) -> date:
    """Try common date formats."""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {value}")


def _csv_txn_hash(txn_date: date, description: str, amount: Decimal) -> str:
    """SHA-256 hash of date|description|amount for deduplication."""
    raw = f"{txn_date}|{description}|{amount}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


@router.post("/bank-connections/upload", response_model=CSVUploadResponse)
async def upload_csv(
    carrier_id: int = Query(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a CSV bank statement. Creates or reuses a manual BankConnection."""
    contents = await file.read()
    text = contents.decode("utf-8-sig")  # handles BOM

    # Detect dialect
    try:
        dialect = csv.Sniffer().sniff(text[:2048])
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV has no headers")

    # Map columns
    date_col = _find_column(reader.fieldnames, ["date", "transaction date", "posted date"])
    desc_col = _find_column(reader.fieldnames, ["description", "memo", "details", "transaction"])
    amount_col = _find_column(reader.fieldnames, ["amount"])
    debit_col = _find_column(reader.fieldnames, ["debit"])
    credit_col = _find_column(reader.fieldnames, ["credit"])

    if not date_col:
        raise HTTPException(status_code=400, detail="CSV missing a date column")
    if not desc_col:
        raise HTTPException(status_code=400, detail="CSV missing a description column")
    if not amount_col and not (debit_col or credit_col):
        raise HTTPException(status_code=400, detail="CSV missing amount/debit/credit columns")

    # Find or create manual connection
    result = await db.execute(
        select(BankConnection).where(
            BankConnection.carrier_id == carrier_id,
            BankConnection.connection_type == ConnectionType.manual,
            BankConnection.is_active == True,  # noqa: E712
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        connection = BankConnection(
            carrier_id=carrier_id,
            institution_name="CSV Upload",
            account_name="Manual Import",
            account_mask="0000",
            connection_type=ConnectionType.manual,
        )
        db.add(connection)
        await db.flush()

    # Fetch existing hashes for dedup
    existing_result = await db.execute(
        select(BankTransaction.transaction_id).where(
            BankTransaction.bank_connection_id == connection.id
        )
    )
    existing_ids = set(existing_result.scalars().all())

    imported = 0
    skipped = 0
    total_rows = 0

    for row in reader:
        total_rows += 1
        try:
            txn_date = _parse_date(row[date_col])
            description = row[desc_col].strip()

            if amount_col:
                raw_amount = row[amount_col].strip().replace(",", "").replace("$", "")
                amount = Decimal(raw_amount)
                is_deposit = amount > 0
                amount = abs(amount)
            else:
                debit_val = (row.get(debit_col, "") or "").strip().replace(",", "").replace("$", "")
                credit_val = (row.get(credit_col, "") or "").strip().replace(",", "").replace("$", "")
                if credit_val and credit_val != "0" and credit_val != "0.00":
                    amount = Decimal(credit_val)
                    is_deposit = True
                elif debit_val and debit_val != "0" and debit_val != "0.00":
                    amount = abs(Decimal(debit_val))
                    is_deposit = False
                else:
                    skipped += 1
                    continue

            txn_id = f"csv-{_csv_txn_hash(txn_date, description, amount)}"

            if txn_id in existing_ids:
                skipped += 1
                continue

            bank_txn = BankTransaction(
                bank_connection_id=connection.id,
                transaction_id=txn_id,
                date=txn_date,
                description=description,
                amount=amount,
                is_deposit=is_deposit,
            )
            db.add(bank_txn)
            existing_ids.add(txn_id)
            imported += 1

        except (ValueError, InvalidOperation, KeyError):
            skipped += 1
            continue

    connection.last_synced_at = datetime.utcnow()
    await db.commit()

    return CSVUploadResponse(imported=imported, skipped=skipped, total_rows=total_rows)


# ---------------------------------------------------------------------------
# Transaction listing
# ---------------------------------------------------------------------------


@router.get("/transactions", response_model=list[BankTransactionResponse])
async def list_transactions(
    bank_connection_id: int = Query(...),
    is_reconciled: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List transactions for a bank connection, with optional reconciliation filter."""
    query = select(BankTransaction).where(
        BankTransaction.bank_connection_id == bank_connection_id
    )
    if is_reconciled is not None:
        query = query.where(BankTransaction.is_reconciled == is_reconciled)
    query = query.order_by(BankTransaction.date.desc())

    result = await db.execute(query)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------


@router.post("/reconcile", response_model=ReconciliationResponse)
async def reconcile(carrier_id: int = Query(...), db: AsyncSession = Depends(get_db)):
    """Match unreconciled deposits to outstanding invoices for a carrier."""
    service = ReconciliationService(db)
    result = await service.reconcile(carrier_id)
    return result


# ---------------------------------------------------------------------------
# Categorization
# ---------------------------------------------------------------------------


@router.post("/transactions/categorize", response_model=CategorizationResponse)
async def categorize_transactions(
    bank_connection_id: int = Query(...), db: AsyncSession = Depends(get_db)
):
    """Categorize uncategorized transactions by keyword matching."""
    service = TransactionCategorizationService(db)
    result = await service.categorize(bank_connection_id)
    return result
