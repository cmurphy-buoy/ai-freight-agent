# PRD: AI Bookkeeper — Invoice Tracking & Bank Reconciliation

## Introduction

Add an AI-powered bookkeeper to the Freight Agent that helps small carriers track invoices from completed loads, connect their business bank account (via Plaid or manual upload), and auto-reconcile payments against outstanding invoices. This eliminates the manual spreadsheet work most owner-operators do today.

The system starts with a mock Plaid data layer so the full pipeline works without API keys. Manual CSV/OFX bank statement upload works as a fallback for carriers whose banks aren't supported or who prefer not to connect directly.

The architecture is designed to be factoring-company-ready — invoices have a `factored` status and a generic `factoring_company` field so a future phase can add API integrations with RTS Financial, Triumph, OTR Solutions, or any other factoring provider.

**Target user:** Owner-operator or small fleet dispatcher who currently tracks invoices in spreadsheets or paper folders and manually checks their bank account to see if brokers have paid.

## Goals

- Track invoices tied to completed loads (broker, amount, due date, status)
- Connect business bank account via Plaid to pull transactions automatically
- Manual bank statement upload (CSV/OFX) as fallback
- Auto-match bank deposits to outstanding invoices (reconciliation)
- AI-assisted categorization of non-invoice transactions (fuel, tolls, maintenance, insurance, etc.)
- Dashboard showing: outstanding invoices, overdue invoices, recent payments, unmatched deposits
- Architecture supports future factoring company integration without schema changes

## User Stories

### US-011: Invoice database model and CRUD API
**Description:** As a carrier, I want to create and track invoices for loads I've hauled so I know who owes me money and when payment is due.

**Acceptance Criteria:**
- [ ] Invoice model: id, carrier_id (FK), load_reference (string — e.g. load_id from search), broker_name, broker_mc, origin_city, origin_state, destination_city, destination_state, amount (decimal), rate_per_mile (decimal), miles (int), invoice_date (date), due_date (date), status (enum: draft, sent, outstanding, paid, overdue, factored, disputed), factoring_company (string, nullable), payment_date (date, nullable), payment_reference (string, nullable), notes (text, nullable), created_at, updated_at
- [ ] Migration creates invoices table with FK to carrier_profiles
- [ ] POST /api/invoices — create an invoice
- [ ] GET /api/invoices/{id} — retrieve an invoice
- [ ] PUT /api/invoices/{id} — update an invoice (status, payment info, notes)
- [ ] GET /api/invoices?carrier_id={id} — list all invoices for a carrier
- [ ] GET /api/invoices?carrier_id={id}&status=outstanding — filter by status
- [ ] Auto-set status to "overdue" logic: any invoice where due_date < today and status is "outstanding" or "sent"
- [ ] Typecheck passes

### US-012: Invoice creation from load search results
**Description:** As a carrier, I want to create an invoice directly from a load I found in search results so I don't have to re-enter all the details.

**Acceptance Criteria:**
- [ ] POST /api/invoices/from-load endpoint that accepts load data (broker_name, broker_mc, origin, destination, rate_total, rate_per_mile, miles) and carrier_id
- [ ] Auto-populates invoice fields from load data
- [ ] Sets invoice_date to today
- [ ] Sets due_date to 30 days from today (standard broker net-30)
- [ ] Sets status to "draft"
- [ ] Returns the created invoice
- [ ] Typecheck passes

### US-013: Bank account connection model and Plaid link setup
**Description:** As a carrier, I want to connect my business bank account so the system can pull my transactions automatically.

**Acceptance Criteria:**
- [ ] BankConnection model: id, carrier_id (FK), institution_name (string), account_name (string), account_mask (string — last 4 digits), connection_type (enum: plaid, manual), plaid_access_token (string, encrypted/nullable), plaid_item_id (string, nullable), is_active (bool, default true), last_synced_at (datetime, nullable), created_at, updated_at
- [ ] Migration creates bank_connections table
- [ ] POST /api/bank-connections/plaid/link — initiates Plaid Link flow (mock: returns a fake access token and test institution)
- [ ] GET /api/bank-connections?carrier_id={id} — list connected accounts
- [ ] DELETE /api/bank-connections/{id} — disconnect an account
- [ ] MockPlaidService in app/services/mock_plaid.py with same interface a real Plaid adapter would use
- [ ] Typecheck passes

### US-014: Bank transaction model and sync endpoint
**Description:** As a developer, I need to store bank transactions pulled from Plaid (or uploaded manually) so the reconciliation engine has data to work with.

**Acceptance Criteria:**
- [ ] BankTransaction model: id, bank_connection_id (FK), transaction_id (string, unique — from Plaid or generated for manual), date (date), description (string), amount (decimal — positive for deposits, negative for debits), category (string, nullable — e.g. "fuel", "toll", "broker_payment", "insurance", "maintenance", "other"), is_deposit (bool), is_reconciled (bool, default false), matched_invoice_id (FK to invoices, nullable), raw_data (JSON, nullable — stores original Plaid response), created_at
- [ ] Migration creates bank_transactions table with FKs
- [ ] POST /api/bank-connections/{id}/sync — pulls transactions from Plaid (mock: generates 30+ realistic transactions)
- [ ] GET /api/transactions?bank_connection_id={id} — list transactions
- [ ] GET /api/transactions?bank_connection_id={id}&is_reconciled=false — list unreconciled transactions
- [ ] MockPlaidService.get_transactions() returns realistic mix: broker payments (deposits), fuel charges, toll charges, insurance debits, maintenance, etc.
- [ ] Typecheck passes

### US-015: Manual bank statement upload (CSV)
**Description:** As a carrier, I want to upload a CSV bank statement if I can't or don't want to connect via Plaid, so I still get reconciliation.

**Acceptance Criteria:**
- [ ] POST /api/bank-connections/upload endpoint accepts a CSV file
- [ ] Creates a BankConnection with connection_type="manual" if one doesn't exist
- [ ] Parses CSV with columns: date, description, amount (negative=debit, positive=credit) — flexible column name matching (e.g. "Date", "DATE", "Transaction Date" all work)
- [ ] Creates BankTransaction records for each row
- [ ] Skips duplicate transactions (matched by date + description + amount)
- [ ] Returns count of imported transactions and count of skipped duplicates
- [ ] Returns 400 with helpful message if CSV format is unrecognizable
- [ ] Typecheck passes

### US-016: Auto-reconciliation engine
**Description:** As a carrier, I want the system to automatically match bank deposits to my outstanding invoices so I know who has paid without manually checking.

**Acceptance Criteria:**
- [ ] ReconciliationService in app/services/reconciliation.py
- [ ] POST /api/reconcile?carrier_id={id} triggers reconciliation
- [ ] Matching logic — a deposit matches an invoice if: (a) amount matches exactly (within $0.50 tolerance for rounding), AND (b) deposit description contains broker name OR broker MC number
- [ ] When matched: set invoice status to "paid", set invoice payment_date to transaction date, set transaction is_reconciled=true and matched_invoice_id
- [ ] Fuzzy matching: normalize broker names (lowercase, strip "logistics", "freight", "inc", "llc", etc.) before comparing
- [ ] Returns summary: { matched_count, unmatched_deposits: [...], newly_paid_invoices: [...] }
- [ ] Does NOT auto-match if multiple invoices could match the same deposit (flags as "needs_review" instead)
- [ ] Typecheck passes

### US-017: AI transaction categorization service
**Description:** As a carrier, I want non-invoice transactions (fuel, tolls, etc.) automatically categorized so I have clean books without manual tagging.

**Acceptance Criteria:**
- [ ] TransactionCategorizationService in app/services/categorization.py
- [ ] POST /api/transactions/categorize?bank_connection_id={id} triggers categorization of uncategorized transactions
- [ ] Rule-based categorization (no LLM needed for MVP): keywords in description → category mapping
- [ ] Categories: fuel (pilot, loves, ta, flying j, fuel, diesel), tolls (ez pass, toll, pike, turnpike), insurance (insurance, progressive, national interstate), maintenance (repair, tire, service, mechanic, parts), lumper (lumper, unload), scale (cat scale, scale), parking (truck stop, parking), subscription (eld, samsara, keeptruckin, motive), broker_payment (matched via reconciliation), other (default)
- [ ] Case-insensitive matching
- [ ] Returns count of categorized transactions by category
- [ ] Typecheck passes

### US-018: Bookkeeper dashboard — invoice management page
**Description:** As a carrier, I want a page to view, create, and manage all my invoices with status indicators.

**Acceptance Criteria:**
- [ ] New tab "Bookkeeper" added to the dashboard navigation
- [ ] Invoice list table: Invoice #, Broker, Route (origin→dest), Amount, Rate/Mi, Invoice Date, Due Date, Status, Actions
- [ ] Status badges color coded: draft (gray), sent (blue), outstanding (yellow), paid (green), overdue (red), factored (purple), disputed (orange)
- [ ] "Create Invoice" form with fields: broker name, broker MC, origin, destination, amount, rate/mile, miles, due date
- [ ] "Mark as Sent" and "Mark as Paid" quick-action buttons on each row
- [ ] Filter dropdown: All, Outstanding, Overdue, Paid
- [ ] Stats row at top: Total Outstanding ($), Total Overdue ($), Paid This Month ($), Total Invoices count
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-019: Bookkeeper dashboard — bank connection and transactions page
**Description:** As a carrier, I want to see my bank transactions and trigger sync/upload from the dashboard.

**Acceptance Criteria:**
- [ ] "Bank" sub-section within the Bookkeeper tab
- [ ] "Connect Bank (Plaid)" button that calls the Plaid link endpoint (mock: immediately creates a test connection)
- [ ] "Upload Statement (CSV)" button with file input
- [ ] Connected accounts list showing: institution name, account (last 4), last synced, sync button
- [ ] Transaction table: Date, Description, Amount (green for deposits, red for debits), Category, Reconciled (✓/✗), Matched Invoice
- [ ] Filter: All, Deposits Only, Unreconciled, By Category dropdown
- [ ] "Sync Now" button pulls latest transactions
- [ ] "Categorize All" button triggers auto-categorization
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-020: Bookkeeper dashboard — reconciliation panel
**Description:** As a carrier, I want a one-click reconciliation button that matches deposits to invoices and shows me what was matched and what needs manual review.

**Acceptance Criteria:**
- [ ] "Reconcile" button in the Bookkeeper tab that calls POST /api/reconcile
- [ ] Results panel shows: number matched, list of newly paid invoices (broker + amount), list of unmatched deposits that need review
- [ ] Unmatched deposits show a dropdown to manually assign to an outstanding invoice
- [ ] Manual assignment calls PUT /api/invoices/{id} to mark as paid and links the transaction
- [ ] After reconciliation, invoice list and transaction list both refresh to show updated statuses
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

## Functional Requirements

- FR-10: System stores invoices with full load details, status lifecycle, and optional factoring company field
- FR-11: Invoices can be created manually or auto-populated from load search results
- FR-12: Bank accounts connect via Plaid (mock first) or manual CSV upload
- FR-13: Bank transactions are stored with date, description, amount, category, and reconciliation status
- FR-14: CSV parser handles common bank statement formats with flexible column name matching
- FR-15: Reconciliation engine matches deposits to invoices by amount + broker name/MC with fuzzy matching
- FR-16: Ambiguous matches (multiple possible invoices) are flagged for manual review, not auto-matched
- FR-17: Transaction categorization uses keyword rules for common trucking expenses
- FR-18: Dashboard shows invoice lifecycle, bank transactions, and reconciliation results in one place
- FR-19: Invoice status enum includes "factored" for future factoring company integration

## Non-Goals (Out of Scope for This Phase)

- No real Plaid API integration (mock only — same pattern as mock DAT)
- No factoring company API integrations (schema supports it, no active connections)
- No OFX/QFX file parsing (CSV only for manual upload)
- No profit/loss reports or financial statements
- No tax categorization or 1099 generation
- No accounts payable (only tracks money owed TO the carrier, not BY the carrier)
- No multi-currency support
- No automatic invoice emailing to brokers

## Technical Considerations

- **Plaid mock pattern**: Same as MockDATService — MockPlaidService follows the interface a real Plaid adapter would use. Swap one file later.
- **Transaction deduplication**: Plaid transactions have a unique transaction_id. Manual uploads deduplicate on (date, description, amount) combo.
- **Reconciliation tolerance**: $0.50 to handle rounding differences between invoice amount and actual deposit.
- **Factoring-ready schema**: Invoice has `status=factored` and `factoring_company` field. A future FactoringService can update these when an invoice is sold to a factor.
- **CSV parsing**: Use Python's csv module with sniffing for delimiter detection. No pandas dependency needed.
- **No encryption MVP**: plaid_access_token is stored as plain text in mock mode. Real Plaid integration phase must add encryption (Fernet or similar).

## Success Metrics

- Carrier can create an invoice from a load in under 3 clicks
- Auto-reconciliation correctly matches 80%+ of broker payments on first run
- Transaction categorization correctly labels 90%+ of common trucking expenses
- Carrier can see total outstanding, overdue, and paid amounts at a glance
- Swapping MockPlaidService for real Plaid requires changing only one file

## Open Questions

- What Plaid plan tier is needed? (affects transaction history depth and cost)
- Should we support OFX/QFX bank statement formats in addition to CSV?
- What's the standard payment terms for each factoring company? (affects due date logic when factored)
- Should overdue invoices auto-trigger an email reminder to the broker? (Phase 3 candidate)
