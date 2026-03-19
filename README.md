# 🚛 AI Freight Agent MVP

An AI-powered freight agent that helps small trucking carriers find and evaluate loads. Built with Python, FastAPI, and PostgreSQL.

## What It Does

1. **Store your carrier profile** — MC#, DOT#, insurance, contact info
2. **Define your truck** — equipment type, weight limits, location, rate floor
3. **Save preferred lanes** — routes you like to run (Atlanta → Dallas, etc.)
4. **Search loads** — finds loads matching your truck from a mock DAT load board
5. **Score & rank loads** — rates each load 0-100 based on rate, deadhead, and lane match

## Quick Start

### 1. Install Python 3.11+
Download from [python.org](https://python.org) if you don't have it.

### 2. Install PostgreSQL
Download from [postgresql.org](https://www.postgresql.org/download/) or use Docker:
```bash
docker run -d --name freight-db -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:16
```

### 3. Create the database
```bash
createdb freight_agent
# Or if using Docker:
docker exec -it freight-db psql -U postgres -c "CREATE DATABASE freight_agent;"
```

### 4. Set up the project
```bash
cd freight-agent
cp .env.example .env          # Then edit .env with your DB password
pip install -r requirements.txt
alembic upgrade head           # Creates all database tables
```

### 5. Run it
```bash
uvicorn app.main:app --reload
```

### 6. Open in your browser
- **Dashboard:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs (interactive — you can test every endpoint)

## How to Use

1. Go to the **Setup** tab → fill in your carrier info → Save
2. Fill in your truck details (use Atlanta: lat 33.749, lng -84.388 for testing) → Save
3. Go to **Preferred Lanes** tab → add routes you like (e.g., Atlanta,GA → Dallas,TX)
4. Go to **Search Loads** tab → select your truck → click Search
5. See loads ranked by score — green (70+) is great, yellow (40-69) is okay, red is meh

## Project Structure

```
freight-agent/
├── app/
│   ├── main.py              ← App entry point, connects everything
│   ├── config.py             ← Settings (reads .env file)
│   ├── db/
│   │   └── database.py       ← Database connection
│   ├── models/
│   │   ├── base.py            ← Base class for all models
│   │   ├── carrier.py         ← CarrierProfile table
│   │   └── truck.py           ← Truck + PreferredLane tables
│   ├── routes/
│   │   ├── health.py          ← GET /health
│   │   ├── carriers.py        ← Carrier CRUD API
│   │   ├── trucks.py          ← Truck + Lanes CRUD API
│   │   └── loads.py           ← Load search endpoint
│   ├── schemas/
│   │   ├── __init__.py        ← Carrier schemas (validation)
│   │   └── trucks.py          ← Truck + Lane schemas
│   ├── services/
│   │   ├── geo.py             ← Haversine distance formula
│   │   ├── mock_dat.py        ← Fake DAT load board (65 loads)
│   │   └── scoring.py         ← Load scoring algorithm (0-100)
│   └── static/
│       └── dashboard.html     ← The web dashboard
├── migrations/                ← Alembic DB migrations
├── alembic.ini
├── requirements.txt
└── prd.json                   ← Ralph stories for future development
```

## Next Steps (Phase 2)

When you're ready to expand, the `prd.json` can be extended with:
- **Real DAT API** — swap `MockDATService` for a real one (same interface)
- **Automated bidding** — submit bids via email or API
- **Carrier packet submission** — auto-send W-9/insurance to new brokers
- **Broker communication** — AI-drafted emails for check calls
- **Multi-user auth** — login system for multiple dispatchers

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
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
| GET | /api/loads/search?truck_id={id} | Search & score loads |
