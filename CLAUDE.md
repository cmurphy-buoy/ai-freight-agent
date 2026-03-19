# CLAUDE.md — AI Freight Agent

## What This Project Is

An AI freight agent MVP for small trucking carriers. It searches a mock DAT load board, filters loads by truck parameters, and scores/ranks them 0-100 so the carrier sees the best loads first.

## Commands

- `uvicorn app.main:app --reload` — Start dev server on port 8000
- `alembic upgrade head` — Run database migrations
- `alembic revision --autogenerate -m "description"` — Create a new migration after model changes
- `python -m pytest` — Run tests (when added)

## Tech Stack

- **Python 3.11+** with **FastAPI** (async web framework)
- **PostgreSQL** via **SQLAlchemy async** (ORM) + **asyncpg** (driver)
- **Alembic** for database migrations
- **Pydantic** for input validation
- Plain HTML + vanilla JS for the dashboard (no frontend framework)

## Project Structure

```
app/
├── main.py              ← App entry point, registers all routers
├── config.py            ← Settings from .env (DATABASE_URL)
├── db/database.py       ← Engine, session factory, get_db dependency
├── models/
│   ├── base.py          ← DeclarativeBase (all models inherit from this)
│   ├── carrier.py       ← CarrierProfile table
│   └── truck.py         ← Truck + PreferredLane tables + EquipmentType enum
├── routes/
│   ├── health.py        ← GET /health
│   ├── carriers.py      ← CRUD for /api/carriers
│   ├── trucks.py        ← CRUD for /api/trucks and /api/trucks/{id}/lanes
│   └── loads.py         ← GET /api/loads/search (main search endpoint)
├── schemas/
│   ├── __init__.py      ← CarrierProfile Pydantic schemas
│   └── trucks.py        ← Truck + PreferredLane Pydantic schemas
├── services/
│   ├── geo.py           ← Haversine distance formula (miles between two lat/lng points)
│   ├── mock_dat.py      ← MockDATService — generates 65 fake loads, Southeast US focus
│   └── scoring.py       ← LoadScoringService — scores loads 0-100
└── static/
    └── dashboard.html   ← Full dashboard UI (setup, search, lanes — all in one file)
```

## Architecture Patterns

- **Service layer pattern**: Routes call services, services call data layer. Never put business logic directly in routes.
- **Mock-first design**: `MockDATService` follows the same interface a real DAT API adapter would use: `search_loads(equipment_type, origin_lat, origin_lng, radius_miles) -> list[dict]`. Swap one file to go live.
- **Dependency injection**: Database sessions are injected via `Depends(get_db)` in routes.

## Key Conventions

- All API routes are prefixed with `/api/` (except /health and dashboard pages)
- Database models live in `app/models/`, one file per table group
- Pydantic schemas live in `app/schemas/`, separate Create/Update/Response classes
- Equipment types are: dry_van, reefer, flatbed, step_deck, power_only
- States are always 2-letter uppercase abbreviations (e.g., "GA", "TX")
- MC numbers are 6 digits, DOT numbers are 7-8 digits

## Scoring Formula (0-100 points)

- **Rate per mile**: 0-40 pts (linear scale, $1.00 above min_rate = max)
- **Deadhead miles**: 0-30 pts (closer to truck = more points)
- **Preferred lane match**: 0-30 pts (full match = priority_weight/10 * 30, partial match = half)

## Database

- PostgreSQL with async connections
- Connection string in `.env` as `DATABASE_URL`
- Format: `postgresql+asyncpg://user:password@host:port/freight_agent`
- Alembic handles migrations — always create a migration after changing models

## Adding New Models

1. Create model file in `app/models/`
2. Import it in `app/models/__init__.py`
3. Run `alembic revision --autogenerate -m "add X table"`
4. Run `alembic upgrade head`

## Adding New Routes

1. Create route file in `app/routes/`
2. Import and register in `app/main.py` with `app.include_router()`

## Swapping Mock Data for Real DAT API

1. Create `app/services/real_dat.py` with class `RealDATService`
2. Implement same method: `search_loads(equipment_type, origin_lat, origin_lng, radius_miles) -> list[dict]`
3. Return same dict shape: load_id, origin_city, origin_state, origin_lat, origin_lng, destination_city, destination_state, dest_lat, dest_lng, equipment_type, weight_lbs, rate_total, rate_per_mile, miles, pickup_date, delivery_date, broker_name, broker_mc
4. In `app/routes/loads.py`, change `MockDATService` import to `RealDATService`

## Development Roadmap

**Phase 1 (COMPLETE):** Load search & scoring MVP — see `prd.json` (US-001 through US-010)
**Phase 2 (COMPLETE):** AI Bookkeeper — see `prd-bookkeeper.json` (US-011 through US-020)

Phase 2 adds:
- Invoice tracking tied to completed loads (draft → sent → outstanding → paid/overdue/factored)
- Bank account connection via Plaid (mock first) or CSV upload
- Auto-reconciliation: matches deposits to invoices by amount + broker name
- Transaction categorization: fuel, tolls, insurance, maintenance, etc.
- Bookkeeper dashboard tab with invoice management, bank transactions, and reconciliation

### Swapping MockPlaidService for Real Plaid

Same pattern as DAT:
1. Create `app/services/real_plaid.py` with class `RealPlaidService`
2. Implement same methods: `create_link(carrier_id)`, `get_transactions(access_token, start_date, end_date)`
3. In `app/routes/bank.py`, change `MockPlaidService` import to `RealPlaidService`

### Factoring Company Integration (Phase 3 candidate)

Schema is already ready — Invoice has `status=factored` and `factoring_company` field. Future FactoringService would:
1. Accept an invoice ID and factoring company name
2. Call factoring company API to submit the invoice
3. Update invoice status to "factored" and set factoring_company field
4. Track advance amount vs. remaining balance

Phase 3+ candidates:
- Real DAT API integration
- Real Plaid API integration
- Factoring company APIs (RTS Financial, Triumph, OTR Solutions)
- Automated bidding
- Carrier packet submission
- Broker communication bot
- Authentication / multi-user
- Profit/loss reports
