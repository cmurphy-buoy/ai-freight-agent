# AI Bookkeeper — Design Spec

**Date:** 2026-03-18
**Phase:** 2 (US-011 through US-020)
**Status:** Approved

## Overview

Add invoice tracking, bank reconciliation, and transaction categorization to the Freight Agent. Carriers track invoices from completed loads, connect their bank account (mock Plaid or CSV upload), and auto-reconcile payments against outstanding invoices.

Target user: Owner-operator or small fleet dispatcher who currently tracks invoices in spreadsheets.

## Implementation Strategy

Two-stream parallel build, then convergence:

```
Stream 1 (Invoice):     US-011 → US-012
Stream 2 (Bank):        US-013 → US-014 → US-015
                              ↘         ↙
Convergence:            US-016 (reconciliation) → US-017 (categorization)
                                    ↓
Dashboard:              US-018 → US-019 → US-020
```

Streams 1 and 2 are built by parallel subagents. Reconciliation, categorization, and dashboard are sequential after both streams complete.

**Data-level coupling note:** MockPlaidService generates deposit descriptions that reference broker names from `BROKER_NAMES` in `mock_dat.py` (import or duplicate a subset). This is a data dependency, not a code dependency — both streams can be built in parallel since the broker names list is stable and read-only.

## Data Models

### Invoice (`app/models/invoice.py`)

```
InvoiceStatus enum: draft, sent, outstanding, paid, overdue, factored, disputed

Invoice table:
  id                  int PK autoincrement
  carrier_id          int FK → carrier_profiles.id
  load_reference      string nullable
  broker_name         string
  broker_mc           string
  origin_city         string
  origin_state        string(2)
  destination_city    string
  destination_state   string(2)
  amount              Numeric(10,2)
  rate_per_mile       Numeric(5,2)
  miles               int
  invoice_date        date
  due_date            date
  status              InvoiceStatus, default=draft
  factoring_company   string nullable
  payment_date        date nullable
  payment_reference   string nullable
  notes               text nullable
  created_at          datetime, server_default=now()
  updated_at          datetime, server_default=now(), onupdate=now()
```

### Bank Connection (`app/models/bank.py`)

```
ConnectionType enum: plaid, manual

BankConnection table:
  id                  int PK autoincrement
  carrier_id          int FK → carrier_profiles.id
  institution_name    string
  account_name        string
  account_mask        string(4)
  connection_type     ConnectionType
  plaid_access_token  string nullable
  plaid_item_id       string nullable
  is_active           bool, default=true
  last_synced_at      datetime nullable
  created_at          datetime, server_default=now()
  updated_at          datetime, server_default=now(), onupdate=now()
```

### Bank Transaction (`app/models/bank.py`)

```
BankTransaction table:
  id                  int PK autoincrement
  bank_connection_id  int FK → bank_connections.id
  transaction_id      string unique
  date                date
  description         string
  amount              Numeric(10,2)  (positive=deposit, negative=debit)
  category            string nullable
  is_deposit          bool  (derived from amount sign; kept for query convenience, always set to amount > 0)
  is_reconciled       bool, default=false
  matched_invoice_id  int FK → invoices.id nullable
  raw_data            JSON nullable
  created_at          datetime, server_default=now()
```

### Relationships

Follow Phase 1 pattern with explicit `relationship()` declarations:
- `Invoice.carrier` → `CarrierProfile` (many-to-one)
- `BankConnection.carrier` → `CarrierProfile` (many-to-one)
- `BankConnection.transactions` → `BankTransaction` (one-to-many, cascade delete-orphan)
- `BankTransaction.bank_connection` → `BankConnection` (many-to-one)
- `BankTransaction.matched_invoice` → `Invoice` (many-to-one, nullable)

### Migration Strategy

Invoice migration runs first (BankTransaction has FK to invoices). Each stream creates its own migration via `alembic revision --autogenerate`. Migrations are applied sequentially before convergence work begins.

## Pydantic Schemas

### Invoice Schemas (`app/schemas/invoices.py`)

- **InvoiceCreate**: carrier_id, broker_name, broker_mc, origin/dest city+state, amount, rate_per_mile, miles, invoice_date (default=date.today()), due_date, notes (optional)
- **InvoiceFromLoadCreate**: carrier_id, broker_name, broker_mc, origin/dest city+state, rate_total, rate_per_mile, miles, load_reference (optional). `rate_total` maps to `Invoice.amount`. Auto-sets invoice_date=today, due_date=today+30, status=draft.
- **InvoiceUpdate**: all fields optional — for status changes, payment info, notes
- **InvoiceResponse**: full model, `from_attributes=True`

No DELETE endpoint for invoices — invoices are never deleted, only status-changed (for audit trail integrity).

### Bank Schemas (`app/schemas/bank.py`)

- **PlaidLinkRequest**: carrier_id (int) — request body for Plaid link endpoint
- **BankConnectionResponse**: id, carrier_id, institution_name, account_name, account_mask, connection_type, is_active, last_synced_at, created_at
- **BankTransactionResponse**: id, transaction_id, date, description, amount, category, is_deposit, is_reconciled, matched_invoice_id, created_at
- **CSVUploadResponse**: `{imported: int, skipped: int, total_rows: int}`
- **ReconciliationResponse**: `{matched_count: int, unmatched_deposits: list, newly_paid_invoices: list, needs_review: list}`
- **CategorizationResponse**: `{categorized_count: int, by_category: dict}`

No create schemas for transactions — those are created internally by sync/upload service calls. PlaidLinkRequest is the only input schema for bank connections.

## API Routes

### Invoice Routes (`app/routes/invoices.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/invoices | Create invoice from form data |
| POST | /api/invoices/from-load | Create invoice auto-populated from load data |
| GET | /api/invoices/{id} | Get single invoice |
| PUT | /api/invoices/{id} | Update invoice (status, payment info, notes) |
| GET | /api/invoices?carrier_id={id} | List all invoices for carrier |
| GET | /api/invoices?carrier_id={id}&status=X | Filter by status |

### Bank Routes (`app/routes/bank.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/bank-connections/plaid/link | Mock Plaid link, creates BankConnection |
| GET | /api/bank-connections?carrier_id={id} | List connected accounts |
| DELETE | /api/bank-connections/{id} | Soft delete (is_active=false) |
| POST | /api/bank-connections/{id}/sync | Pull transactions via MockPlaidService |
| POST | /api/bank-connections/upload | CSV upload (carrier_id + file), creates/reuses manual connection + transactions |
| GET | /api/transactions?bank_connection_id={id} | List transactions |
| GET | /api/transactions?bank_connection_id={id}&is_reconciled=false | Filter unreconciled |
| POST | /api/reconcile?carrier_id={id} | Trigger auto-reconciliation (lives in bank.py despite top-level path) |
| POST | /api/transactions/categorize?bank_connection_id={id} | Trigger categorization |

All routes registered in `app/main.py` via `app.include_router()`.

## Services

### MockPlaidService (`app/services/mock_plaid.py`)

Same swap pattern as MockDATService.

**Methods:**
- `create_link(carrier_id)` → returns fake access_token, item_id, institution_name ("First National Bank"), account_name ("Business Checking"), account_mask ("4521")
- `get_transactions(access_token, start_date, end_date)` → generates 30+ transactions

**Mock transaction mix:**
- Clean matches: deposits with exact broker names from MockDATService (e.g., "DEPOSIT - Apex Freight MC#384291")
- Messy matches: truncated/abbreviated names (e.g., "ACH DEPOSIT COYOTE LOG", "WIRE TQL LOGIS")
- Unmatched deposits: random company names not in mock loads (e.g., "ACH DEPOSIT SMITH HAULING")
- Expenses: fuel (Pilot, Loves), tolls (EZ Pass), insurance, maintenance, lumper, scale, parking, subscriptions

### ReconciliationService (`app/services/reconciliation.py`)

- Queries outstanding/sent/overdue invoices + unreconciled deposits for a carrier
- Match logic: amount within $0.50 tolerance AND description contains broker_name or broker_mc
- Fuzzy name normalization: lowercase, strip suffixes (logistics, freight, inc, llc, corp, co, transportation, trucking, brokerage, services, group)
- On match: invoice status → paid, invoice payment_date → transaction date, transaction is_reconciled → true, transaction matched_invoice_id → invoice id
- On ambiguous match (multiple invoices for one deposit): skip auto-match, add to needs_review
- On ambiguous reverse (multiple deposits for one invoice): match the first chronological deposit, leave others unmatched
- Skips invoices already marked as paid (idempotent — safe to run multiple times)
- Only processes deposits where is_reconciled=false and invoices where status in (outstanding, sent, overdue)
- Returns: matched_count, unmatched_deposits, newly_paid_invoices, needs_review

### TransactionCategorizationService (`app/services/categorization.py`)

- Keyword-to-category rules, case-insensitive on description
- Categories: fuel (pilot, loves, ta petro, flying j, fuel, diesel, gas), tolls (ez pass, ezpass, toll, pike, turnpike, ipass), insurance (insurance, progressive, national interstate, great west), maintenance (repair, tire, service, mechanic, parts, shop, freightliner, peterbilt, kenworth), lumper (lumper, unload), scale (cat scale, scale), parking (truck stop, parking, truckpark), subscription (eld, samsara, keeptruckin, motive, project44), broker_payment (already reconciled), other (default)
- Only categorizes where category is null
- Returns categorized_count + breakdown by_category

## Dashboard UI

Extends existing `dashboard.html` with a new **Bookkeeper** tab. Single-file approach, matching Phase 1 pattern.

### Invoice Management (US-018)

- Stats row: Total Outstanding ($), Total Overdue ($), Paid This Month ($), Invoice Count
- Create Invoice form: broker name, broker MC, origin/dest city+state, amount, rate/mile, miles, due date
- Invoice table: Invoice #, Broker, Route, Amount, Rate/Mi, Invoice Date, Due Date, Status badge, Actions
- Status badge colors: draft (gray), sent (blue), outstanding (yellow), paid (green), overdue (red), factored (purple), disputed (orange)
- Quick actions: Mark as Sent, Mark as Paid
- Filter: All, Outstanding, Overdue, Paid, Draft

### Bank & Transactions (US-019)

- Connect Bank (Plaid) button — mock link, immediately shows connection
- Upload Statement (CSV) button with file input
- Connected accounts list: institution, last 4, last synced, Sync Now button
- Transaction table: Date, Description, Amount (green/red), Category badge, Reconciled check, Matched Invoice
- Filters: All, Deposits Only, Unreconciled, category dropdown
- Categorize All button

### Reconciliation Panel (US-020)

- Reconcile Now button → POST /api/reconcile
- Results: matched count, newly paid list, unmatched deposits list
- Needs Review: deposits with multiple possible matches
- Unmatched deposits: dropdown to manually assign to outstanding invoice
- Auto-refresh invoice + transaction lists after reconciliation

All interactions via fetch() with no page reloads.

## CSV Upload Specification

**Column matching** (case-insensitive, flexible naming):
- Date column: "Date", "Transaction Date", "Posted Date", "DATE"
- Description column: "Description", "Memo", "Details", "Transaction"
- Amount column: "Amount", "AMOUNT" (single column, negative=debit, positive=credit)
- Alternate: separate "Debit" and "Credit" columns (both positive values)

**Processing:**
- Uses Python `csv.Sniffer` for delimiter detection (comma, tab, pipe)
- Generates `transaction_id` as SHA-256 hash of `f"{date}|{description}|{amount}"` to enable deduplication
- Reuses existing manual BankConnection for the same carrier (queries for `carrier_id + connection_type=manual`), creates one if none exists
- Skips rows where transaction_id already exists in DB
- Returns 400 if no recognized columns found
- No file size limit for MVP (reasonable assumption: bank statements are small)

## Architecture Decisions

1. **Factoring-ready schema**: Invoice has `status=factored` and `factoring_company` field. No active factoring integrations in this phase.
2. **Mock-first pattern**: MockPlaidService follows same interface as a real Plaid adapter. Swap one file to go live.
3. **CSV parsing**: Python csv module with Sniffer for delimiter detection. No pandas dependency.
4. **No encryption**: plaid_access_token stored as plain text in mock mode. Real Plaid integration must add encryption.
5. **Reconciliation tolerance**: $0.50 to handle rounding differences.
6. **Transaction deduplication**: Plaid uses transaction_id uniqueness. CSV upload deduplicates on (date, description, amount).
7. **Single-file dashboard**: Bookkeeper tab added to existing dashboard.html, matching Phase 1 pattern.

## New Files Created

```
app/models/invoice.py
app/models/bank.py
app/schemas/invoices.py
app/schemas/bank.py
app/routes/invoices.py
app/routes/bank.py
app/services/mock_plaid.py
app/services/reconciliation.py
app/services/categorization.py
migrations/versions/xxx_add_invoices_table.py    (autogenerated)
migrations/versions/xxx_add_bank_tables.py       (autogenerated)
```

## Modified Files

```
app/models/__init__.py      — import new models
app/main.py                 — register new routers
app/static/dashboard.html   — add Bookkeeper tab with 3 sub-sections
```
