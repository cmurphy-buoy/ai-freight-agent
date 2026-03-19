# AI Freight Agent

An AI-powered freight agent for small trucking carriers. Search loads from DAT and Truckstop, score and rank them, book loads, manage invoices, connect bank accounts, and auto-reconcile payments.

**Live Demo:** [relaxed-driscoll.vercel.app](https://relaxed-driscoll.vercel.app)

## What It Does

### Phase 1: Load Search & Scoring (Complete)
- Store carrier profile (MC#, DOT#, contact info)
- Define trucks with equipment type, weight limits, location, rate floor
- Save preferred lanes (routes you like to run)
- Search 200 mock loads from DAT and Truckstop load boards
- Score and rank loads 0-100 based on rate, deadhead distance, and lane match
- Browse all loads without a truck, filter by equipment type and origin state
- Book loads directly from search results

### Phase 2: AI Bookkeeper (Complete)
- Invoice tracking tied to booked loads (draft, sent, outstanding, paid, overdue, factored, disputed)
- Create invoices manually or auto-generate from booked loads
- Bank account connection via mock Plaid integration
- CSV bank statement upload with flexible column matching
- Auto-reconciliation: matches deposits to invoices by amount + fuzzy broker name
- Transaction categorization: fuel, tolls, insurance, maintenance, lumper, scale, parking, subscriptions
- Bookkeeper dashboard with invoice management, bank transactions, and reconciliation panel

### Phase 3+ (Planned)
- Real DAT API integration (swap MockDATService for RealDATService)
- Real Truckstop API integration (same swap pattern)
- Real Plaid API integration (swap MockPlaidService for RealPlaidService)
- Factoring company APIs (RTS Financial, Triumph, OTR Solutions)
- Driver dispatch workflow
- Automated bidding
- Carrier packet submission
- Broker communication bot
- Authentication / multi-user
- Profit/loss reports

## Tech Stack

- **Python 3.11+** with **FastAPI** (async web framework)
- **PostgreSQL** via **SQLAlchemy async** + **asyncpg**
- **Alembic** for database migrations
- **Pydantic** for input validation
- Plain HTML + vanilla JS dashboard (no frontend framework)
- **Vercel** for deployment (serverless Python + Neon PostgreSQL)

## Quick Start

### Local Development

```bash
# Clone and setup
git clone https://github.com/cmurphy-buoy/ai-freight-agent.git
cd ai-freight-agent
cp .env.example .env          # Edit with your DB credentials
pip install -r requirements.txt

# Database
createdb freight_agent
alembic upgrade head

# Run
uvicorn app.main:app --reload
# Open http://localhost:8000
```

### Demo Flow

1. **Setup tab** - Save a carrier profile, add trucks (use Atlanta, Nashville, Charlotte, or Dallas)
2. **Search Loads** - Browse 200 loads from DAT + Truckstop, filter by type/state
3. **Book** a load - Click "Book" to create a draft invoice
4. **Bookkeeper tab** - See invoices, connect mock bank, sync transactions
5. **Reconcile** - Click "Reconcile Now" to auto-match deposits to invoices
6. **Categorize** - Click "Categorize All" to tag expenses (fuel, tolls, etc.)

## API Endpoints

### Carrier & Truck Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/carriers | Create carrier profile |
| GET | /api/carriers/{id} | Get carrier profile |
| PUT | /api/carriers/{id} | Update carrier profile |
| POST | /api/trucks | Create truck |
| GET | /api/trucks/{id} | Get truck |
| PUT | /api/trucks/{id} | Update truck |
| GET | /api/trucks?carrier_id={id} | List trucks for carrier |
| POST | /api/trucks/{id}/lanes | Add preferred lane |
| GET | /api/trucks/{id}/lanes | List lanes for truck |
| DELETE | /api/trucks/{id}/lanes/{lid} | Remove a lane |

### Load Search
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/loads/search?truck_id={id} | Search and score loads for a truck |
| GET | /api/loads/browse | Browse all loads (no truck required) |

### Invoices
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/invoices | Create invoice |
| POST | /api/invoices/from-load | Create invoice from booked load |
| GET | /api/invoices/{id} | Get invoice |
| PUT | /api/invoices/{id} | Update invoice (status, payment) |
| GET | /api/invoices?carrier_id={id} | List invoices (optional status filter) |

### Bank and Transactions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/bank-connections/plaid/link | Connect bank via mock Plaid |
| GET | /api/bank-connections?carrier_id={id} | List bank connections |
| DELETE | /api/bank-connections/{id} | Disconnect bank |
| POST | /api/bank-connections/{id}/sync | Sync transactions |
| POST | /api/bank-connections/upload | Upload CSV statement |
| GET | /api/transactions?bank_connection_id={id} | List transactions |
| POST | /api/reconcile?carrier_id={id} | Run auto-reconciliation |
| POST | /api/transactions/categorize?bank_connection_id={id} | Categorize expenses |

## Scoring Formula (0-100 points)

- **Rate per mile**: 0-40 pts (linear scale, $1.00 above min_rate = max)
- **Deadhead miles**: 0-30 pts (closer to truck = more points)
- **Preferred lane match**: 0-30 pts (full match = priority_weight/10 * 30)

## Architecture

- **Mock-first design**: MockDATService, MockTruckstopService, and MockPlaidService follow the same interfaces their real API adapters would use. Swap one file to go live.
- **Service layer pattern**: Routes call services, services call data layer. No business logic in routes.
- **Multi-board aggregation**: Search merges results from DAT and Truckstop, scores them identically.
- **Fuzzy reconciliation**: Strips common suffixes (Logistics, Inc, LLC, etc.) for broker name matching.
