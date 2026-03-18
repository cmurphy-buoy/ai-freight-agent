# AI Bookkeeper Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add invoice tracking, bank reconciliation, and transaction categorization to the Freight Agent so carriers can track payments without spreadsheets.

**Architecture:** Two-stream parallel build (invoice backend + bank backend), then convergence (reconciliation + categorization), then dashboard. Service layer pattern — routes call services, services call data layer. Mock-first design for Plaid, matching the existing MockDATService swap pattern.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy async, asyncpg, Alembic, Pydantic, vanilla HTML/JS

**Spec:** `docs/superpowers/specs/2026-03-18-ai-bookkeeper-design.md`

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `app/models/invoice.py` | Invoice model + InvoiceStatus enum |
| `app/models/bank.py` | BankConnection + BankTransaction models + ConnectionType enum |
| `app/schemas/invoices.py` | InvoiceCreate, InvoiceFromLoadCreate, InvoiceUpdate, InvoiceResponse |
| `app/schemas/bank.py` | PlaidLinkRequest, BankConnectionResponse, BankTransactionResponse, CSVUploadResponse, ReconciliationResponse, CategorizationResponse |
| `app/routes/invoices.py` | Invoice CRUD + from-load creation |
| `app/routes/bank.py` | Bank connection, transaction sync/upload, reconciliation, categorization routes |
| `app/services/mock_plaid.py` | MockPlaidService — fake Plaid link + transaction generation |
| `app/services/reconciliation.py` | ReconciliationService — matches deposits to invoices |
| `app/services/categorization.py` | TransactionCategorizationService — keyword-based expense categorization |
| `tests/test_invoices.py` | Invoice model, schema, and route tests |
| `tests/test_bank.py` | Bank connection, transaction, sync, CSV upload tests |
| `tests/test_reconciliation.py` | Reconciliation service tests |
| `tests/test_categorization.py` | Categorization service tests |
| `tests/conftest.py` | Shared test fixtures (async DB session, test client, carrier/truck factory) |

### Modified Files

| File | Change |
|------|--------|
| `app/models/__init__.py` | Import Invoice, InvoiceStatus, BankConnection, BankTransaction, ConnectionType |
| `app/main.py` | Register invoices_router and bank_router |
| `app/static/dashboard.html` | Add Bookkeeper tab with invoice management, bank/transactions, reconciliation panel |
| `requirements.txt` | Add httpx and pytest-asyncio for testing |

---

## Stream 1: Invoice Backend (US-011, US-012)

> **Parallelizable with Stream 2.** No dependencies on bank models.

### Task 1: Invoice Model + Migration

**Files:**
- Create: `app/models/invoice.py`
- Modify: `app/models/__init__.py`

- [ ] **Step 1: Create Invoice model**

Create `app/models/invoice.py` with:

```python
import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    outstanding = "outstanding"
    paid = "paid"
    overdue = "overdue"
    factored = "factored"
    disputed = "disputed"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey("carrier_profiles.id"), nullable=False)
    load_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    broker_name: Mapped[str] = mapped_column(String(200), nullable=False)
    broker_mc: Mapped[str] = mapped_column(String(6), nullable=False)
    origin_city: Mapped[str] = mapped_column(String(100), nullable=False)
    origin_state: Mapped[str] = mapped_column(String(2), nullable=False)
    destination_city: Mapped[str] = mapped_column(String(100), nullable=False)
    destination_state: Mapped[str] = mapped_column(String(2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    rate_per_mile: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    miles: Mapped[int] = mapped_column(Integer, nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), nullable=False, default=InvoiceStatus.draft)
    factoring_company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    carrier: Mapped["CarrierProfile"] = relationship("CarrierProfile")
```

- [ ] **Step 2: Register in models __init__**

Add to `app/models/__init__.py`:

```python
from app.models.invoice import Invoice, InvoiceStatus
```

And add `Invoice`, `InvoiceStatus` to `__all__`.

- [ ] **Step 3: Generate and run migration**

Run:
```bash
alembic revision --autogenerate -m "add invoices table"
alembic upgrade head
```

Expected: Migration creates `invoices` table with FK to `carrier_profiles`.

- [ ] **Step 4: Commit**

```bash
git add app/models/invoice.py app/models/__init__.py migrations/
git commit -m "feat: add Invoice model and migration (US-011)"
```

### Task 2: Invoice Schemas

**Files:**
- Create: `app/schemas/invoices.py`

- [ ] **Step 1: Create invoice schemas**

Create `app/schemas/invoices.py` with:

```python
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.models.invoice import InvoiceStatus


class InvoiceCreate(BaseModel):
    carrier_id: int
    broker_name: str
    broker_mc: str
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    amount: Decimal
    rate_per_mile: Decimal
    miles: int
    invoice_date: date | None = None  # defaults to today in route
    due_date: date
    notes: str | None = None

    @field_validator("origin_state", "destination_state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        if len(v) != 2:
            raise ValueError("State must be 2-letter abbreviation")
        return v.upper()

    @field_validator("broker_mc")
    @classmethod
    def validate_mc(cls, v: str) -> str:
        if not v.isdigit() or len(v) > 6:
            raise ValueError("broker_mc must be up to 6 digits")
        return v


class InvoiceFromLoadCreate(BaseModel):
    carrier_id: int
    broker_name: str
    broker_mc: str
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    rate_total: Decimal  # maps to Invoice.amount
    rate_per_mile: Decimal
    miles: int
    load_reference: str | None = None


class InvoiceUpdate(BaseModel):
    status: InvoiceStatus | None = None
    payment_date: date | None = None
    payment_reference: str | None = None
    notes: str | None = None
    factoring_company: str | None = None
    due_date: date | None = None


class InvoiceResponse(BaseModel):
    id: int
    carrier_id: int
    load_reference: str | None
    broker_name: str
    broker_mc: str
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    amount: Decimal
    rate_per_mile: Decimal
    miles: int
    invoice_date: date
    due_date: date
    status: InvoiceStatus
    factoring_company: str | None
    payment_date: date | None
    payment_reference: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Commit**

```bash
git add app/schemas/invoices.py
git commit -m "feat: add Invoice Pydantic schemas (US-011)"
```

### Task 3: Invoice Routes

**Files:**
- Create: `app/routes/invoices.py`
- Modify: `app/main.py`

- [ ] **Step 1: Create invoice routes**

Create `app/routes/invoices.py` with all 6 endpoints:

```python
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
    # Verify carrier exists
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
```

- [ ] **Step 2: Register router in main.py**

Add to `app/main.py`:

```python
from app.routes.invoices import router as invoices_router
```

And:

```python
app.include_router(invoices_router)
```

- [ ] **Step 3: Verify server starts**

Run: `uvicorn app.main:app --reload`

Check: `curl http://localhost:8000/docs` shows invoice endpoints.

- [ ] **Step 4: Commit**

```bash
git add app/routes/invoices.py app/main.py
git commit -m "feat: add Invoice CRUD and from-load routes (US-011, US-012)"
```

---

## Stream 2: Bank Backend (US-013, US-014, US-015)

> **Parallelizable with Stream 1.** Depends on Invoice model only for the BankTransaction.matched_invoice_id FK — but this FK is nullable so the migration can be created after the invoices migration exists.

### Task 4: Bank Models + Migration

**Files:**
- Create: `app/models/bank.py`
- Modify: `app/models/__init__.py`

- [ ] **Step 1: Create bank models**

Create `app/models/bank.py` with BankConnection and BankTransaction:

```python
import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Integer,
    JSON, Numeric, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ConnectionType(str, enum.Enum):
    plaid = "plaid"
    manual = "manual"


class BankConnection(Base):
    __tablename__ = "bank_connections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey("carrier_profiles.id"), nullable=False)
    institution_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_mask: Mapped[str] = mapped_column(String(4), nullable=False)
    connection_type: Mapped[ConnectionType] = mapped_column(Enum(ConnectionType), nullable=False)
    plaid_access_token: Mapped[str | None] = mapped_column(String(200), nullable=True)
    plaid_item_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    carrier: Mapped["CarrierProfile"] = relationship("CarrierProfile")
    transactions: Mapped[list["BankTransaction"]] = relationship(
        "BankTransaction", back_populates="bank_connection", cascade="all, delete-orphan"
    )


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bank_connection_id: Mapped[int] = mapped_column(ForeignKey("bank_connections.id"), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_deposit: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    matched_invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    bank_connection: Mapped["BankConnection"] = relationship("BankConnection", back_populates="transactions")
    matched_invoice: Mapped["Invoice | None"] = relationship("Invoice")
```

- [ ] **Step 2: Register in models __init__**

Add to `app/models/__init__.py`:

```python
from app.models.bank import BankConnection, BankTransaction, ConnectionType
```

And add to `__all__`.

- [ ] **Step 3: Generate and run migration**

Run (must run AFTER invoices migration exists):
```bash
alembic revision --autogenerate -m "add bank_connections and bank_transactions tables"
alembic upgrade head
```

Expected: Creates `bank_connections` and `bank_transactions` tables with FKs.

- [ ] **Step 4: Commit**

```bash
git add app/models/bank.py app/models/__init__.py migrations/
git commit -m "feat: add BankConnection and BankTransaction models (US-013, US-014)"
```

### Task 5: MockPlaidService

**Files:**
- Create: `app/services/mock_plaid.py`

- [ ] **Step 1: Create MockPlaidService**

Create `app/services/mock_plaid.py`:

```python
import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.services.mock_dat import BROKER_NAMES


def _generate_transaction_id() -> str:
    return f"plaid-txn-{uuid.uuid4().hex[:12]}"


class MockPlaidService:
    """
    Simulates the Plaid API.

    Same swap pattern as MockDATService:
    1. Create RealPlaidService with same methods
    2. Swap import in app/routes/bank.py
    """

    def __init__(self, seed: int | None = 42):
        if seed is not None:
            random.seed(seed)
        self._seed = seed

    def create_link(self, carrier_id: int) -> dict:
        return {
            "access_token": f"mock-access-{carrier_id}-{uuid.uuid4().hex[:8]}",
            "item_id": f"mock-item-{carrier_id}",
            "institution_name": "First National Bank",
            "account_name": "Business Checking",
            "account_mask": "4521",
        }

    def get_transactions(
        self, access_token: str, start_date: date, end_date: date
    ) -> list[dict]:
        if self._seed is not None:
            random.seed(self._seed)

        transactions = []
        current = start_date

        # Generate ~35 transactions spread across the date range
        broker_subset = random.sample(BROKER_NAMES, min(6, len(BROKER_NAMES)))

        # Clean broker deposits (exact names)
        for i, broker in enumerate(broker_subset[:3]):
            mc = str(random.randint(100000, 999999))
            txn_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
            amount = round(random.uniform(800, 4500), 2)
            transactions.append({
                "transaction_id": _generate_transaction_id(),
                "date": str(txn_date),
                "description": f"DEPOSIT - {broker} MC#{mc}",
                "amount": amount,
            })

        # Messy broker deposits (abbreviated/truncated)
        messy_formats = [
            "ACH DEPOSIT {} LOG",
            "WIRE {} FRGHT",
            "DEP {} TRANS",
            "ACH CR {}",
        ]
        for i, broker in enumerate(broker_subset[3:]):
            short_name = broker.split()[0].upper()
            txn_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
            amount = round(random.uniform(1000, 5000), 2)
            fmt = random.choice(messy_formats)
            transactions.append({
                "transaction_id": _generate_transaction_id(),
                "date": str(txn_date),
                "description": fmt.format(short_name),
                "amount": amount,
            })

        # Unmatched deposits (random companies not in broker list)
        unmatched_companies = ["Smith Hauling", "Quick Transport LLC", "Midwest Carriers"]
        for company in unmatched_companies:
            txn_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
            amount = round(random.uniform(500, 3000), 2)
            transactions.append({
                "transaction_id": _generate_transaction_id(),
                "date": str(txn_date),
                "description": f"ACH DEPOSIT {company.upper()}",
                "amount": amount,
            })

        # Expense transactions (negative amounts)
        expenses = [
            ("PILOT TRAVEL CENTER #4521", -random.uniform(200, 600)),
            ("LOVES COUNTRY STORE #312", -random.uniform(150, 500)),
            ("FLYING J #1892", -random.uniform(180, 450)),
            ("EZ PASS REPLENISH", -random.uniform(25, 75)),
            ("TOLLWAY AUTHORITY", -random.uniform(5, 30)),
            ("PROGRESSIVE INSURANCE PMT", -random.uniform(800, 1500)),
            ("NATIONAL INTERSTATE INS", -random.uniform(600, 1200)),
            ("PETERBILT SERVICE CTR", -random.uniform(300, 2000)),
            ("DISCOUNT TIRE #0891", -random.uniform(200, 800)),
            ("FREIGHTLINER DEALER SVC", -random.uniform(400, 1500)),
            ("LUMPER SERVICE - WAREHOUSE", -random.uniform(50, 150)),
            ("CAT SCALE #2847", -random.uniform(10, 15)),
            ("TRUCK STOP PARKING OVERNIGHT", -random.uniform(15, 30)),
            ("SAMSARA ELD MONTHLY", -random.uniform(25, 45)),
            ("MOTIVE KEEPTRUCKIN SUB", -random.uniform(20, 40)),
            ("ATM WITHDRAWAL", -random.uniform(40, 200)),
            ("WALMART SUPERCENTER", -random.uniform(20, 100)),
            ("DRIVER PAYROLL DIRECT DEP", -random.uniform(1500, 3500)),
        ]
        for desc, amt in expenses:
            txn_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
            transactions.append({
                "transaction_id": _generate_transaction_id(),
                "date": str(txn_date),
                "description": desc,
                "amount": round(amt, 2),
            })

        random.seed()  # Reset seed
        return sorted(transactions, key=lambda t: t["date"])
```

- [ ] **Step 2: Commit**

```bash
git add app/services/mock_plaid.py
git commit -m "feat: add MockPlaidService with realistic transaction mix (US-013, US-014)"
```

### Task 6: Bank Schemas

**Files:**
- Create: `app/schemas/bank.py`

- [ ] **Step 1: Create bank schemas**

Create `app/schemas/bank.py`:

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add app/schemas/bank.py
git commit -m "feat: add bank Pydantic schemas (US-013, US-014, US-015)"
```

### Task 7: Bank Routes — Connection + Sync + CSV Upload

**Files:**
- Create: `app/routes/bank.py`
- Modify: `app/main.py`

- [ ] **Step 1: Create bank routes**

Create `app/routes/bank.py` with all bank connection, transaction, and upload endpoints:

```python
import csv
import hashlib
import io
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.bank import BankConnection, BankTransaction, ConnectionType
from app.models.carrier import CarrierProfile
from app.schemas.bank import (
    BankConnectionResponse, BankTransactionResponse,
    CSVUploadResponse, PlaidLinkRequest,
)
from app.services.mock_plaid import MockPlaidService

router = APIRouter(tags=["bank"])

plaid_service = MockPlaidService(seed=42)


# --- Bank Connection Endpoints ---

@router.post("/api/bank-connections/plaid/link", response_model=BankConnectionResponse, status_code=201)
async def plaid_link(data: PlaidLinkRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CarrierProfile).where(CarrierProfile.id == data.carrier_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="carrier_id does not exist")

    link_data = plaid_service.create_link(data.carrier_id)
    conn = BankConnection(
        carrier_id=data.carrier_id,
        institution_name=link_data["institution_name"],
        account_name=link_data["account_name"],
        account_mask=link_data["account_mask"],
        connection_type=ConnectionType.plaid,
        plaid_access_token=link_data["access_token"],
        plaid_item_id=link_data["item_id"],
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return conn


@router.get("/api/bank-connections", response_model=list[BankConnectionResponse])
async def list_bank_connections(
    carrier_id: int = Query(...), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(BankConnection).where(
            BankConnection.carrier_id == carrier_id,
            BankConnection.is_active == True,
        )
    )
    return result.scalars().all()


@router.delete("/api/bank-connections/{connection_id}", status_code=204)
async def delete_bank_connection(connection_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BankConnection).where(BankConnection.id == connection_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Bank connection not found")
    conn.is_active = False
    await db.commit()


# --- Transaction Sync ---

@router.post("/api/bank-connections/{connection_id}/sync", response_model=list[BankTransactionResponse])
async def sync_transactions(connection_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BankConnection).where(BankConnection.id == connection_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Bank connection not found")
    if not conn.is_active:
        raise HTTPException(status_code=400, detail="Bank connection is inactive")

    from datetime import date, timedelta
    end = date.today()
    start = end - timedelta(days=30)
    raw_txns = plaid_service.get_transactions(conn.plaid_access_token, start, end)

    new_txns = []
    for txn in raw_txns:
        # Dedup by transaction_id
        existing = await db.execute(
            select(BankTransaction).where(BankTransaction.transaction_id == txn["transaction_id"])
        )
        if existing.scalar_one_or_none():
            continue

        amount = float(txn["amount"])
        bt = BankTransaction(
            bank_connection_id=connection_id,
            transaction_id=txn["transaction_id"],
            date=txn["date"],
            description=txn["description"],
            amount=txn["amount"],
            is_deposit=amount > 0,
            raw_data=txn,
        )
        db.add(bt)
        new_txns.append(bt)

    conn.last_synced_at = datetime.now()
    await db.commit()
    for bt in new_txns:
        await db.refresh(bt)
    return new_txns


# --- CSV Upload ---

DATE_COLUMNS = {"date", "transaction date", "posted date"}
DESC_COLUMNS = {"description", "memo", "details", "transaction"}
AMOUNT_COLUMNS = {"amount"}
DEBIT_COLUMNS = {"debit"}
CREDIT_COLUMNS = {"credit"}


def _find_column(headers: list[str], candidates: set[str]) -> int | None:
    for i, h in enumerate(headers):
        if h.strip().lower() in candidates:
            return i
    return None


def _hash_transaction(date_str: str, desc: str, amount: str) -> str:
    raw = f"{date_str}|{desc}|{amount}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


@router.post("/api/bank-connections/upload", response_model=CSVUploadResponse)
async def upload_csv(
    carrier_id: int = Query(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # Verify carrier
    result = await db.execute(select(CarrierProfile).where(CarrierProfile.id == carrier_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="carrier_id does not exist")

    content = (await file.read()).decode("utf-8-sig")

    # Detect delimiter
    try:
        dialect = csv.Sniffer().sniff(content[:2048])
    except csv.Error:
        dialect = csv.excel

    reader = csv.reader(io.StringIO(content), dialect)
    headers = next(reader, None)
    if not headers:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    date_col = _find_column(headers, DATE_COLUMNS)
    desc_col = _find_column(headers, DESC_COLUMNS)
    amount_col = _find_column(headers, AMOUNT_COLUMNS)
    debit_col = _find_column(headers, DEBIT_COLUMNS)
    credit_col = _find_column(headers, CREDIT_COLUMNS)

    if date_col is None or desc_col is None:
        raise HTTPException(status_code=400, detail="CSV must have Date and Description columns")
    if amount_col is None and (debit_col is None or credit_col is None):
        raise HTTPException(status_code=400, detail="CSV must have Amount column or Debit/Credit columns")

    # Get or create manual bank connection
    result = await db.execute(
        select(BankConnection).where(
            BankConnection.carrier_id == carrier_id,
            BankConnection.connection_type == ConnectionType.manual,
            BankConnection.is_active == True,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        conn = BankConnection(
            carrier_id=carrier_id,
            institution_name="Manual Upload",
            account_name="Uploaded Statements",
            account_mask="0000",
            connection_type=ConnectionType.manual,
        )
        db.add(conn)
        await db.flush()

    imported = 0
    skipped = 0
    total = 0

    for row in reader:
        if not row or all(c.strip() == "" for c in row):
            continue
        total += 1

        try:
            date_str = row[date_col].strip()
            desc = row[desc_col].strip()

            if amount_col is not None:
                amount_str = row[amount_col].strip().replace(",", "").replace("$", "")
                amount = float(amount_str)
            else:
                debit_str = row[debit_col].strip().replace(",", "").replace("$", "")
                credit_str = row[credit_col].strip().replace(",", "").replace("$", "")
                debit = float(debit_str) if debit_str else 0
                credit = float(credit_str) if credit_str else 0
                amount = credit - debit

            txn_id = _hash_transaction(date_str, desc, str(amount))

            # Dedup check
            existing = await db.execute(
                select(BankTransaction).where(BankTransaction.transaction_id == txn_id)
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            bt = BankTransaction(
                bank_connection_id=conn.id,
                transaction_id=txn_id,
                date=date_str,
                description=desc,
                amount=amount,
                is_deposit=amount > 0,
            )
            db.add(bt)
            imported += 1
        except (ValueError, IndexError):
            skipped += 1
            continue

    conn.last_synced_at = datetime.now()
    await db.commit()
    return CSVUploadResponse(imported=imported, skipped=skipped, total_rows=total)


# --- Transaction List ---

@router.get("/api/transactions", response_model=list[BankTransactionResponse])
async def list_transactions(
    bank_connection_id: int = Query(...),
    is_reconciled: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(BankTransaction).where(BankTransaction.bank_connection_id == bank_connection_id)
    if is_reconciled is not None:
        query = query.where(BankTransaction.is_reconciled == is_reconciled)
    query = query.order_by(BankTransaction.date.desc())
    result = await db.execute(query)
    return result.scalars().all()
```

- [ ] **Step 2: Register router in main.py**

Add to `app/main.py`:

```python
from app.routes.bank import router as bank_router
```

And:

```python
app.include_router(bank_router)
```

- [ ] **Step 3: Verify server starts and endpoints appear**

Run: `uvicorn app.main:app --reload`

Check: `curl http://localhost:8000/docs` shows bank endpoints.

- [ ] **Step 4: Commit**

```bash
git add app/routes/bank.py app/main.py
git commit -m "feat: add bank connection, sync, CSV upload, and transaction routes (US-013, US-014, US-015)"
```

---

## Convergence: Reconciliation + Categorization (US-016, US-017)

> **Sequential.** Depends on both Stream 1 (invoices) and Stream 2 (bank transactions) being complete.

### Task 8: Reconciliation Service

**Files:**
- Create: `app/services/reconciliation.py`

- [ ] **Step 1: Create ReconciliationService**

Create `app/services/reconciliation.py`:

```python
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
        # Get all outstanding/sent/overdue invoices
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

        # Get all unreconciled deposits across active bank connections
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
```

- [ ] **Step 2: Add reconciliation route to bank.py**

Add to `app/routes/bank.py`:

```python
from app.services.reconciliation import ReconciliationService
from app.schemas.bank import ReconciliationResponse

@router.post("/api/reconcile", response_model=ReconciliationResponse)
async def reconcile(carrier_id: int = Query(...), db: AsyncSession = Depends(get_db)):
    service = ReconciliationService(db)
    result = await service.reconcile(carrier_id)
    return result
```

- [ ] **Step 3: Commit**

```bash
git add app/services/reconciliation.py app/routes/bank.py
git commit -m "feat: add ReconciliationService with fuzzy matching (US-016)"
```

### Task 9: Categorization Service

**Files:**
- Create: `app/services/categorization.py`

- [ ] **Step 1: Create TransactionCategorizationService**

Create `app/services/categorization.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank import BankTransaction

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "fuel": ["pilot", "loves", "ta petro", "flying j", "fuel", "diesel", "gas"],
    "tolls": ["ez pass", "ezpass", "toll", "pike", "turnpike", "ipass"],
    "insurance": ["insurance", "progressive", "national interstate", "great west"],
    "maintenance": [
        "repair", "tire", "service", "mechanic", "parts", "shop",
        "freightliner", "peterbilt", "kenworth",
    ],
    "lumper": ["lumper", "unload"],
    "scale": ["cat scale", "scale"],
    "parking": ["truck stop", "parking", "truckpark"],
    "subscription": ["eld", "samsara", "keeptruckin", "motive", "project44"],
}


class TransactionCategorizationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def categorize(self, bank_connection_id: int) -> dict:
        result = await self.db.execute(
            select(BankTransaction).where(
                BankTransaction.bank_connection_id == bank_connection_id,
                BankTransaction.category.is_(None),
            )
        )
        transactions = list(result.scalars().all())

        counts: dict[str, int] = {}
        total = 0

        for txn in transactions:
            # Already reconciled = broker_payment
            if txn.is_reconciled:
                txn.category = "broker_payment"
                counts["broker_payment"] = counts.get("broker_payment", 0) + 1
                total += 1
                continue

            desc_lower = txn.description.lower()
            matched_category = "other"

            for category, keywords in CATEGORY_KEYWORDS.items():
                if any(kw in desc_lower for kw in keywords):
                    matched_category = category
                    break

            txn.category = matched_category
            counts[matched_category] = counts.get(matched_category, 0) + 1
            total += 1

        await self.db.commit()

        return {
            "categorized_count": total,
            "by_category": counts,
        }
```

- [ ] **Step 2: Add categorization route to bank.py**

Add to `app/routes/bank.py`:

```python
from app.services.categorization import TransactionCategorizationService
from app.schemas.bank import CategorizationResponse

@router.post("/api/transactions/categorize", response_model=CategorizationResponse)
async def categorize_transactions(
    bank_connection_id: int = Query(...), db: AsyncSession = Depends(get_db)
):
    service = TransactionCategorizationService(db)
    result = await service.categorize(bank_connection_id)
    return result
```

- [ ] **Step 3: Commit**

```bash
git add app/services/categorization.py app/routes/bank.py
git commit -m "feat: add TransactionCategorizationService with keyword rules (US-017)"
```

---

## Dashboard (US-018, US-019, US-020)

> **Sequential.** Depends on all backend APIs being complete.

### Task 10: Bookkeeper Dashboard — All Three Sections (US-018, US-019, US-020)

**Files:**
- Modify: `app/static/dashboard.html`

- [ ] **Step 1: Read the existing dashboard.html**

Read the full `app/static/dashboard.html` to understand the existing tab structure, CSS variables, and JS patterns. The existing tabs are: Setup, Preferred Lanes, Search Loads. Match the exact CSS classes, button styles, table styles, and fetch() patterns.

- [ ] **Step 2: Add Bookkeeper tab navigation button**

Add a "Bookkeeper" button to the existing tab navigation bar, matching the style of existing tab buttons. Wire it to show/hide the bookkeeper content section using the same JS tab-switching pattern.

- [ ] **Step 3: Add Invoice Management section**

Add to the Bookkeeper tab content area:

**Stats row** — 4 cards in a row:
```html
<div class="stats-row">
  <div class="stat-card"><h3 id="stat-outstanding">$0.00</h3><p>Outstanding</p></div>
  <div class="stat-card"><h3 id="stat-overdue">$0.00</h3><p>Overdue</p></div>
  <div class="stat-card"><h3 id="stat-paid-month">$0.00</h3><p>Paid This Month</p></div>
  <div class="stat-card"><h3 id="stat-invoice-count">0</h3><p>Total Invoices</p></div>
</div>
```

**Filter dropdown + Create Invoice button:**
```html
<div class="controls-row">
  <select id="invoice-filter" onchange="loadInvoices()">
    <option value="">All</option>
    <option value="outstanding">Outstanding</option>
    <option value="overdue">Overdue</option>
    <option value="paid">Paid</option>
    <option value="draft">Draft</option>
  </select>
  <button onclick="showCreateInvoiceForm()">Create Invoice</button>
</div>
```

**Create Invoice form** (hidden by default, toggled by button):
- Fields: broker_name (text), broker_mc (text), origin_city (text), origin_state (text, 2 chars), destination_city (text), destination_state (text, 2 chars), amount (number), rate_per_mile (number), miles (number), due_date (date)
- Submit calls `POST /api/invoices` with carrier_id from the Setup tab's saved carrier

**Invoice table:**
```html
<table id="invoice-table">
  <thead>
    <tr>
      <th>Invoice #</th><th>Broker</th><th>Route</th><th>Amount</th>
      <th>Rate/Mi</th><th>Invoice Date</th><th>Due Date</th><th>Status</th><th>Actions</th>
    </tr>
  </thead>
  <tbody id="invoice-tbody"></tbody>
</table>
```

**Status badge CSS:**
```css
.badge-draft { background: #6b7280; color: white; }
.badge-sent { background: #3b82f6; color: white; }
.badge-outstanding { background: #eab308; color: black; }
.badge-paid { background: #22c55e; color: white; }
.badge-overdue { background: #ef4444; color: white; }
.badge-factored { background: #a855f7; color: white; }
.badge-disputed { background: #f97316; color: white; }
```

**JS functions:**
- `loadInvoices()` — calls `GET /api/invoices?carrier_id={id}&status={filter}`, populates table, updates stats
- `createInvoice(formData)` — calls `POST /api/invoices`, refreshes table
- `markInvoiceAs(invoiceId, status)` — calls `PUT /api/invoices/{id}` with {status: status}, refreshes table

Quick-action buttons per row: "Mark as Sent" (if draft), "Mark as Paid" (if outstanding/sent/overdue)

- [ ] **Step 4: Add Bank & Transactions section**

Add below invoices, within the Bookkeeper tab:

**Bank connection controls:**
```html
<div class="bank-controls">
  <button onclick="connectBankPlaid()">Connect Bank (Plaid)</button>
  <button onclick="document.getElementById('csv-file').click()">Upload Statement (CSV)</button>
  <input type="file" id="csv-file" accept=".csv" style="display:none" onchange="uploadCSV(this)">
</div>
```

**Connected accounts list:**
```html
<div id="bank-connections-list"></div>
```
Each item shows: institution name, "...4521", last synced time, "Sync Now" button

**Transaction controls:**
```html
<div class="controls-row">
  <select id="txn-filter" onchange="loadTransactions()">
    <option value="all">All</option>
    <option value="deposits">Deposits Only</option>
    <option value="unreconciled">Unreconciled</option>
  </select>
  <select id="txn-category-filter" onchange="loadTransactions()">
    <option value="">All Categories</option>
    <option value="fuel">Fuel</option>
    <option value="tolls">Tolls</option>
    <option value="insurance">Insurance</option>
    <option value="maintenance">Maintenance</option>
    <option value="other">Other</option>
  </select>
  <button onclick="categorizeAll()">Categorize All</button>
</div>
```

**Transaction table:**
```html
<table id="txn-table">
  <thead>
    <tr>
      <th>Date</th><th>Description</th><th>Amount</th>
      <th>Category</th><th>Reconciled</th><th>Matched Invoice</th>
    </tr>
  </thead>
  <tbody id="txn-tbody"></tbody>
</table>
```

Amount text: green for positive (deposits), red for negative (debits).

**JS functions:**
- `connectBankPlaid()` — calls `POST /api/bank-connections/plaid/link` with {carrier_id}, refreshes connections list
- `uploadCSV(input)` — reads file, calls `POST /api/bank-connections/upload?carrier_id={id}` with FormData, shows import count
- `loadBankConnections()` — calls `GET /api/bank-connections?carrier_id={id}`, populates list
- `syncTransactions(connectionId)` — calls `POST /api/bank-connections/{id}/sync`, refreshes transaction table
- `loadTransactions()` — calls `GET /api/transactions?bank_connection_id={id}` with filters, populates table
- `categorizeAll()` — calls `POST /api/transactions/categorize?bank_connection_id={id}`, refreshes table

- [ ] **Step 5: Add Reconciliation panel**

Add at top of Bookkeeper tab, above invoices:

```html
<div class="reconciliation-panel">
  <button onclick="runReconciliation()" class="btn-primary">Reconcile Now</button>
  <div id="reconciliation-results" style="display:none">
    <div class="result-summary">
      <span id="recon-matched">0 matched</span>
    </div>
    <div id="recon-newly-paid"></div>
    <div id="recon-unmatched"></div>
    <div id="recon-needs-review"></div>
  </div>
</div>
```

**JS functions:**
- `runReconciliation()` — calls `POST /api/reconcile?carrier_id={id}`, displays results:
  - Shows matched count
  - Lists newly paid invoices (broker name + amount)
  - Lists unmatched deposits with dropdown to manually assign to outstanding invoice
  - Lists needs_review deposits with possible invoice matches
- `manualAssign(depositId, invoiceId)` — calls `PUT /api/invoices/{invoiceId}` with {status: "paid", payment_date: deposit.date}, then marks transaction as reconciled
- After reconciliation: calls `loadInvoices()` and `loadTransactions()` to refresh both tables

**Unmatched deposit row with manual assignment:**
```html
<div class="unmatched-row">
  <span>$1,500.00 - ACH DEPOSIT SMITH HAULING (2026-03-05)</span>
  <select onchange="manualAssign(depositId, this.value)">
    <option value="">Assign to invoice...</option>
    <!-- populated from outstanding invoices -->
  </select>
</div>
```

- [ ] **Step 6: Verify full flow in browser**

Run: `uvicorn app.main:app --reload`

Full test flow:
1. Create carrier + truck (Setup tab)
2. Search loads (Search tab)
3. Switch to Bookkeeper tab
4. Create invoices manually or via API
5. Mark invoices as "sent" then "outstanding"
6. Connect bank (Plaid button)
7. Sync transactions
8. Click Categorize All — verify categories appear
9. Click Reconcile Now — verify matches, unmatched, needs_review
10. Manually assign an unmatched deposit to an invoice
11. Verify invoice and transaction tables refresh with updated statuses

- [ ] **Step 7: Commit**

```bash
git add app/static/dashboard.html app/static/style.css
git commit -m "feat: add Bookkeeper dashboard with invoices, bank, and reconciliation (US-018, US-019, US-020)"
```

---

## Task 11: Tests

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_invoices.py`
- Create: `tests/test_bank.py`
- Create: `tests/test_reconciliation.py`
- Create: `tests/test_categorization.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Add test dependencies to requirements.txt**

Add to `requirements.txt`:

```
httpx==0.27.0
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 2: Create test fixtures**

Create `tests/conftest.py`:

```python
import asyncio
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database import get_db
from app.main import app
from app.models.base import Base
from app.models.carrier import CarrierProfile
from app.models.invoice import Invoice, InvoiceStatus
from app.models.bank import BankConnection, BankTransaction, ConnectionType


# Use a separate test database
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/freight_agent_test"

engine = create_async_engine(TEST_DATABASE_URL)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSession() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def carrier(db):
    c = CarrierProfile(
        company_name="Test Trucking",
        mc_number="123456",
        dot_number="1234567",
        contact_name="John",
        contact_email="john@test.com",
        contact_phone="555-0100",
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@pytest_asyncio.fixture
async def sample_invoice(db, carrier):
    inv = Invoice(
        carrier_id=carrier.id,
        broker_name="Apex Freight",
        broker_mc="384291",
        origin_city="Atlanta",
        origin_state="GA",
        destination_city="Dallas",
        destination_state="TX",
        amount=Decimal("2500.00"),
        rate_per_mile=Decimal("2.50"),
        miles=1000,
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=InvoiceStatus.outstanding,
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv


@pytest_asyncio.fixture
async def bank_connection(db, carrier):
    conn = BankConnection(
        carrier_id=carrier.id,
        institution_name="First National Bank",
        account_name="Business Checking",
        account_mask="4521",
        connection_type=ConnectionType.plaid,
        plaid_access_token="mock-token",
        plaid_item_id="mock-item",
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return conn
```

- [ ] **Step 3: Create invoice tests**

Create `tests/test_invoices.py`:

```python
import pytest
from datetime import date, timedelta


@pytest.mark.asyncio
async def test_create_invoice(client, carrier):
    resp = await client.post("/api/invoices", json={
        "carrier_id": carrier.id,
        "broker_name": "Test Broker",
        "broker_mc": "123456",
        "origin_city": "Atlanta",
        "origin_state": "GA",
        "destination_city": "Dallas",
        "destination_state": "TX",
        "amount": 2000.00,
        "rate_per_mile": 2.50,
        "miles": 800,
        "due_date": str(date.today() + timedelta(days=30)),
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["broker_name"] == "Test Broker"
    assert data["status"] == "draft"
    assert data["invoice_date"] == str(date.today())


@pytest.mark.asyncio
async def test_create_invoice_from_load(client, carrier):
    resp = await client.post("/api/invoices/from-load", json={
        "carrier_id": carrier.id,
        "broker_name": "Load Broker",
        "broker_mc": "654321",
        "origin_city": "Nashville",
        "origin_state": "TN",
        "destination_city": "Miami",
        "destination_state": "FL",
        "rate_total": 3000.00,
        "rate_per_mile": 3.00,
        "miles": 1000,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["amount"] == "3000.00"
    assert data["status"] == "draft"
    assert data["due_date"] == str(date.today() + timedelta(days=30))


@pytest.mark.asyncio
async def test_get_invoice(client, sample_invoice):
    resp = await client.get(f"/api/invoices/{sample_invoice.id}")
    assert resp.status_code == 200
    assert resp.json()["broker_name"] == "Apex Freight"


@pytest.mark.asyncio
async def test_get_invoice_not_found(client):
    resp = await client.get("/api/invoices/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_invoice_status(client, sample_invoice):
    resp = await client.put(f"/api/invoices/{sample_invoice.id}", json={
        "status": "paid",
        "payment_date": str(date.today()),
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "paid"


@pytest.mark.asyncio
async def test_list_invoices_filter_status(client, carrier, sample_invoice):
    resp = await client.get(f"/api/invoices?carrier_id={carrier.id}&status=outstanding")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert all(inv["status"] == "outstanding" for inv in data)


@pytest.mark.asyncio
async def test_create_invoice_invalid_carrier(client):
    resp = await client.post("/api/invoices", json={
        "carrier_id": 99999,
        "broker_name": "Bad",
        "broker_mc": "111111",
        "origin_city": "A",
        "origin_state": "GA",
        "destination_city": "B",
        "destination_state": "TX",
        "amount": 100,
        "rate_per_mile": 1,
        "miles": 100,
        "due_date": str(date.today()),
    })
    assert resp.status_code == 400
```

- [ ] **Step 4: Create bank tests**

Create `tests/test_bank.py`:

```python
import io
import pytest


@pytest.mark.asyncio
async def test_plaid_link(client, carrier):
    resp = await client.post("/api/bank-connections/plaid/link", json={
        "carrier_id": carrier.id,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["institution_name"] == "First National Bank"
    assert data["connection_type"] == "plaid"


@pytest.mark.asyncio
async def test_list_bank_connections(client, carrier, bank_connection):
    resp = await client.get(f"/api/bank-connections?carrier_id={carrier.id}")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_delete_bank_connection(client, bank_connection):
    resp = await client.delete(f"/api/bank-connections/{bank_connection.id}")
    assert resp.status_code == 204
    # Should not appear in active list after delete
    resp2 = await client.get(f"/api/bank-connections?carrier_id={bank_connection.carrier_id}")
    assert all(c["id"] != bank_connection.id for c in resp2.json())


@pytest.mark.asyncio
async def test_sync_transactions(client, bank_connection):
    resp = await client.post(f"/api/bank-connections/{bank_connection.id}/sync")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    # Should have mix of deposits and debits
    amounts = [float(t["amount"]) for t in data]
    assert any(a > 0 for a in amounts)  # deposits
    assert any(a < 0 for a in amounts)  # debits


@pytest.mark.asyncio
async def test_csv_upload(client, carrier):
    csv_content = "Date,Description,Amount\n2026-03-01,PILOT FUEL,-250.00\n2026-03-02,DEPOSIT BROKER,1500.00\n"
    resp = await client.post(
        f"/api/bank-connections/upload?carrier_id={carrier.id}",
        files={"file": ("statement.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 2
    assert data["skipped"] == 0


@pytest.mark.asyncio
async def test_csv_upload_dedup(client, carrier):
    csv_content = "Date,Description,Amount\n2026-03-01,SAME TXN,100.00\n"
    # Upload twice
    await client.post(
        f"/api/bank-connections/upload?carrier_id={carrier.id}",
        files={"file": ("s.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    resp = await client.post(
        f"/api/bank-connections/upload?carrier_id={carrier.id}",
        files={"file": ("s.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.json()["skipped"] == 1
    assert resp.json()["imported"] == 0


@pytest.mark.asyncio
async def test_csv_upload_bad_format(client, carrier):
    csv_content = "Foo,Bar,Baz\n1,2,3\n"
    resp = await client.post(
        f"/api/bank-connections/upload?carrier_id={carrier.id}",
        files={"file": ("bad.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 400
```

- [ ] **Step 5: Create reconciliation tests**

Create `tests/test_reconciliation.py`:

```python
from datetime import date
from decimal import Decimal

import pytest

from app.models.bank import BankTransaction
from app.models.invoice import Invoice, InvoiceStatus
from app.services.reconciliation import ReconciliationService, _normalize_name


def test_normalize_name():
    assert _normalize_name("Apex Freight") == "apex"
    assert _normalize_name("TQL Logistics") == "tql"
    assert _normalize_name("CH Robinson Inc") == "ch robinson"
    assert _normalize_name("  Coyote  Logistics  LLC  ") == "coyote"


@pytest.mark.asyncio
async def test_reconcile_exact_match(db, carrier, sample_invoice, bank_connection):
    # Create a deposit matching the invoice
    txn = BankTransaction(
        bank_connection_id=bank_connection.id,
        transaction_id="test-match-1",
        date=date.today(),
        description="DEPOSIT - Apex Freight MC#384291",
        amount=Decimal("2500.00"),
        is_deposit=True,
    )
    db.add(txn)
    await db.commit()

    service = ReconciliationService(db)
    result = await service.reconcile(carrier.id)

    assert result["matched_count"] == 1
    assert len(result["newly_paid_invoices"]) == 1
    assert result["newly_paid_invoices"][0]["broker_name"] == "Apex Freight"


@pytest.mark.asyncio
async def test_reconcile_within_tolerance(db, carrier, sample_invoice, bank_connection):
    # $0.30 difference — should still match
    txn = BankTransaction(
        bank_connection_id=bank_connection.id,
        transaction_id="test-tolerance-1",
        date=date.today(),
        description="DEPOSIT - Apex Freight",
        amount=Decimal("2500.30"),
        is_deposit=True,
    )
    db.add(txn)
    await db.commit()

    service = ReconciliationService(db)
    result = await service.reconcile(carrier.id)
    assert result["matched_count"] == 1


@pytest.mark.asyncio
async def test_reconcile_unmatched(db, carrier, sample_invoice, bank_connection):
    txn = BankTransaction(
        bank_connection_id=bank_connection.id,
        transaction_id="test-unmatched-1",
        date=date.today(),
        description="ACH DEPOSIT UNKNOWN COMPANY",
        amount=Decimal("999.00"),
        is_deposit=True,
    )
    db.add(txn)
    await db.commit()

    service = ReconciliationService(db)
    result = await service.reconcile(carrier.id)
    assert result["matched_count"] == 0
    assert len(result["unmatched_deposits"]) == 1


@pytest.mark.asyncio
async def test_reconcile_idempotent(db, carrier, sample_invoice, bank_connection):
    txn = BankTransaction(
        bank_connection_id=bank_connection.id,
        transaction_id="test-idemp-1",
        date=date.today(),
        description="DEPOSIT - Apex Freight",
        amount=Decimal("2500.00"),
        is_deposit=True,
    )
    db.add(txn)
    await db.commit()

    service = ReconciliationService(db)
    r1 = await service.reconcile(carrier.id)
    assert r1["matched_count"] == 1

    # Run again — should find nothing new
    r2 = await service.reconcile(carrier.id)
    assert r2["matched_count"] == 0
```

- [ ] **Step 6: Create categorization tests**

Create `tests/test_categorization.py`:

```python
from datetime import date
from decimal import Decimal

import pytest

from app.models.bank import BankTransaction
from app.services.categorization import TransactionCategorizationService


@pytest.mark.asyncio
async def test_categorize_fuel(db, bank_connection):
    txn = BankTransaction(
        bank_connection_id=bank_connection.id,
        transaction_id="cat-fuel-1",
        date=date.today(),
        description="PILOT TRAVEL CENTER #4521",
        amount=Decimal("-350.00"),
        is_deposit=False,
    )
    db.add(txn)
    await db.commit()

    service = TransactionCategorizationService(db)
    result = await service.categorize(bank_connection.id)
    assert result["by_category"].get("fuel", 0) >= 1


@pytest.mark.asyncio
async def test_categorize_tolls(db, bank_connection):
    txn = BankTransaction(
        bank_connection_id=bank_connection.id,
        transaction_id="cat-toll-1",
        date=date.today(),
        description="EZ PASS REPLENISH",
        amount=Decimal("-50.00"),
        is_deposit=False,
    )
    db.add(txn)
    await db.commit()

    service = TransactionCategorizationService(db)
    result = await service.categorize(bank_connection.id)
    assert result["by_category"].get("tolls", 0) >= 1


@pytest.mark.asyncio
async def test_categorize_does_not_overwrite(db, bank_connection):
    txn = BankTransaction(
        bank_connection_id=bank_connection.id,
        transaction_id="cat-existing-1",
        date=date.today(),
        description="PILOT FUEL",
        amount=Decimal("-100.00"),
        is_deposit=False,
        category="manual_override",
    )
    db.add(txn)
    await db.commit()

    service = TransactionCategorizationService(db)
    result = await service.categorize(bank_connection.id)
    # Should not have touched the already-categorized transaction
    await db.refresh(txn)
    assert txn.category == "manual_override"


@pytest.mark.asyncio
async def test_categorize_other_default(db, bank_connection):
    txn = BankTransaction(
        bank_connection_id=bank_connection.id,
        transaction_id="cat-other-1",
        date=date.today(),
        description="RANDOM UNKNOWN PURCHASE",
        amount=Decimal("-25.00"),
        is_deposit=False,
    )
    db.add(txn)
    await db.commit()

    service = TransactionCategorizationService(db)
    result = await service.categorize(bank_connection.id)
    assert result["by_category"].get("other", 0) >= 1
```

- [ ] **Step 7: Run tests**

Run: `pytest tests/ -v`

Expected: All tests pass (requires `freight_agent_test` database to exist).

- [ ] **Step 8: Commit**

```bash
git add tests/ requirements.txt
git commit -m "test: add test suite for invoices, bank, reconciliation, and categorization"
```

---

## Task 12: Final Integration + Verification

- [ ] **Step 1: Verify all endpoints work**

Run: `uvicorn app.main:app --reload`

Check: `curl http://localhost:8000/docs` shows all new endpoints:
- /api/invoices (POST, GET)
- /api/invoices/{id} (GET, PUT)
- /api/invoices/from-load (POST)
- /api/bank-connections/plaid/link (POST)
- /api/bank-connections (GET)
- /api/bank-connections/{id} (DELETE)
- /api/bank-connections/{id}/sync (POST)
- /api/bank-connections/upload (POST)
- /api/transactions (GET)
- /api/reconcile (POST)
- /api/transactions/categorize (POST)

- [ ] **Step 2: Verify typecheck passes**

Run: `python -m mypy app/ --ignore-missing-imports` (if mypy is available, otherwise skip)

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete AI Bookkeeper Phase 2 (US-011 through US-020)"
```

---

## Parallelization Guide

| Task | Stream | Can Parallel With | Blocking Dependency |
|------|--------|-------------------|---------------------|
| Task 1-3 | Stream 1 (Invoice) | Tasks 4-7 (except migration) | None |
| Task 4 Steps 1-2 | Stream 2 (Bank) | Tasks 1-3 | None (code only) |
| Task 4 Step 3 | Stream 2 (Bank) | — | **BLOCKS on Task 1 Step 3** (invoices migration must exist for FK) |
| Task 5-7 | Stream 2 (Bank) | Tasks 1-3 | Task 4 Step 3 |
| Task 8-9 | Convergence | Each other (truly independent) | Tasks 1-7 all done |
| Task 10 | Dashboard | — | Tasks 1-9 done |
| Task 11 | Tests | — | Tasks 1-9 done (can parallel with 10) |
| Task 12 | Integration | — | All done |

**Subagent assignment:**
- Subagent A: Tasks 1, 2, 3 (Invoice stream)
- Subagent B: Tasks 4 (steps 1-2 only), 5, 6 (Bank stream — code files, no migration yet)
- **Sync point:** After Subagent A completes Task 1 Step 3 (invoices migration), Subagent B runs Task 4 Step 3 (bank migration), then Task 7
- Main thread: Tasks 8, 9 (can run in parallel), then 10 + 11 (can parallel), then 12
