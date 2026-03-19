# PRD: AI Freight Agent MVP

## Introduction

Build an AI-powered freight agent that helps small trucking carriers find and evaluate loads from the DAT load board. The MVP focuses on storing company/truck parameters, searching for loads that match those parameters, and scoring/ranking results so the carrier sees the best loads first.

The system starts with mock DAT data so the full pipeline can be built and tested without API access. A real DAT API integration can be swapped in later without changing the rest of the system.

**Target user:** Owner-operator or small fleet dispatcher who currently searches load boards manually.

## Goals

- Store carrier profile (MC#, DOT#, equipment type, insurance info)
- Store truck parameters (location, equipment, weight limits, preferred lanes, rate floor)
- Search for loads matching truck parameters (equipment type, origin radius, destination, weight)
- Score and rank loads by profitability (rate per mile, deadhead distance, lane preference)
- Display results in a simple web dashboard
- Architecture is "API-ready" — mock data layer can be replaced with real DAT API

## User Stories

### US-001: Project scaffolding and database setup
**Description:** As a developer, I need the project structure and database so all other stories have a foundation to build on.

**Acceptance Criteria:**
- [ ] FastAPI project with standard folder structure (app/, app/models/, app/routes/, app/services/, app/db/)
- [ ] PostgreSQL connection via SQLAlchemy async
- [ ] Alembic configured for migrations
- [ ] Health check endpoint GET /health returns {"status": "ok"}
- [ ] Requirements.txt with all dependencies
- [ ] Typecheck passes

### US-002: Carrier profile database model and CRUD API
**Description:** As a carrier, I want to store my company info so the system knows who I am when submitting packets or bids later.

**Acceptance Criteria:**
- [ ] CarrierProfile model: id, company_name, mc_number, dot_number, insurance_provider, insurance_policy_number, insurance_expiry (date), contact_name, contact_email, contact_phone, created_at, updated_at
- [ ] Migration creates carrier_profiles table
- [ ] POST /api/carriers — create a carrier profile
- [ ] GET /api/carriers/{id} — retrieve a carrier profile
- [ ] PUT /api/carriers/{id} — update a carrier profile
- [ ] Input validation on mc_number (6 digits) and dot_number (7-8 digits)
- [ ] Typecheck passes

### US-003: Truck parameters database model and CRUD API
**Description:** As a carrier, I want to define my truck's capabilities and preferences so the system only shows loads my truck can actually haul.

**Acceptance Criteria:**
- [ ] Truck model: id, carrier_id (FK), name/label, equipment_type (enum: dry_van, reefer, flatbed, step_deck, power_only), max_weight_lbs (int), current_city, current_state, current_lat, current_lng, max_deadhead_miles (int), min_rate_per_mile (decimal), created_at, updated_at
- [ ] Migration creates trucks table with FK to carrier_profiles
- [ ] POST /api/trucks — create truck (requires carrier_id)
- [ ] GET /api/trucks/{id} — retrieve truck
- [ ] PUT /api/trucks/{id} — update truck (especially current location)
- [ ] GET /api/trucks?carrier_id={id} — list all trucks for a carrier
- [ ] Typecheck passes

### US-004: Preferred lanes database model and API
**Description:** As a carrier, I want to save my preferred lanes (routes I like to run) so the system can prioritize loads on those routes.

**Acceptance Criteria:**
- [ ] PreferredLane model: id, truck_id (FK), origin_city, origin_state, destination_city, destination_state, priority_weight (int 1-10, default 5)
- [ ] Migration creates preferred_lanes table with FK to trucks
- [ ] POST /api/trucks/{truck_id}/lanes — add a preferred lane
- [ ] GET /api/trucks/{truck_id}/lanes — list preferred lanes for a truck
- [ ] DELETE /api/trucks/{truck_id}/lanes/{lane_id} — remove a lane
- [ ] Typecheck passes

### US-005: Mock DAT load data service
**Description:** As a developer, I need a mock data layer that returns realistic load listings so I can build and test the search/filter pipeline without a real API key.

**Acceptance Criteria:**
- [ ] MockDATService class in app/services/mock_dat.py
- [ ] Generates 50+ realistic mock loads with: load_id, origin_city, origin_state, origin_lat, origin_lng, destination_city, destination_state, dest_lat, dest_lng, equipment_type, weight_lbs, rate_total, rate_per_mile, miles, pickup_date, delivery_date, broker_name, broker_mc
- [ ] Loads cover variety of equipment types, origins (Southeast US focus), and rate ranges ($1.50-$4.00/mile)
- [ ] Method: search_loads(equipment_type, origin_lat, origin_lng, radius_miles) returns filtered list
- [ ] Service follows same interface that a real DAT API adapter would use (so it can be swapped later)
- [ ] Typecheck passes

### US-006: Load search and filter endpoint
**Description:** As a carrier, I want to search for available loads that match my truck's equipment type and are near my truck's current location.

**Acceptance Criteria:**
- [ ] GET /api/loads/search?truck_id={id} endpoint
- [ ] Reads truck's equipment_type, current location, max_deadhead_miles from database
- [ ] Calls MockDATService.search_loads() with those parameters
- [ ] Filters out loads exceeding truck's max_weight_lbs
- [ ] Returns list of matching loads as JSON
- [ ] Each result includes: load details + deadhead_miles (distance from truck to pickup)
- [ ] Typecheck passes

### US-007: Load scoring and ranking service
**Description:** As a carrier, I want search results ranked by how good they are for me — factoring in rate, deadhead, and whether the load is on a preferred lane.

**Acceptance Criteria:**
- [ ] LoadScoringService in app/services/scoring.py
- [ ] Score formula considers: rate_per_mile (higher = better), deadhead_miles (lower = better), preferred_lane_match (bonus points if origin→destination matches a saved lane)
- [ ] Score is 0-100 scale
- [ ] GET /api/loads/search?truck_id={id} now returns results sorted by score descending
- [ ] Each result includes: score, score_breakdown (object showing points from each factor)
- [ ] Typecheck passes

### US-008: Simple web dashboard — carrier setup page
**Description:** As a carrier, I want a simple web page to enter my company info and truck parameters instead of using raw API calls.

**Acceptance Criteria:**
- [ ] HTML page served at GET / with two forms: Carrier Profile and Truck Setup
- [ ] Carrier form fields: company name, MC#, DOT#, contact name, email, phone
- [ ] Truck form fields: label, equipment type (dropdown), max weight, current city/state, max deadhead, min rate per mile
- [ ] Forms submit via JavaScript fetch() to the API endpoints
- [ ] Success/error messages display on page
- [ ] Uses simple CSS (no framework needed) — clean and readable
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-009: Simple web dashboard — load search results page
**Description:** As a carrier, I want to see matching loads in a table so I can quickly scan and decide which to pursue.

**Acceptance Criteria:**
- [ ] HTML page served at GET /dashboard
- [ ] Dropdown to select which truck to search for
- [ ] "Search Loads" button triggers GET /api/loads/search?truck_id={id}
- [ ] Results displayed in a table: Score, Origin, Destination, Miles, Rate/Mile, Total Rate, Deadhead, Equipment, Pickup Date, Broker
- [ ] Table sorted by score (best first)
- [ ] Score column uses color coding: green (70+), yellow (40-69), red (below 40)
- [ ] Empty state message when no loads match
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

### US-010: Preferred lanes UI on dashboard
**Description:** As a carrier, I want to add/remove preferred lanes from the dashboard so I don't have to use API calls.

**Acceptance Criteria:**
- [ ] Section on dashboard page to manage preferred lanes for selected truck
- [ ] Form: origin city/state, destination city/state, priority weight (1-10 slider)
- [ ] List of existing lanes with delete button
- [ ] Adding/removing a lane and re-searching shows updated scores
- [ ] Typecheck passes
- [ ] Verify in browser using dev-browser skill

## Functional Requirements

- FR-1: System stores carrier profiles with MC#, DOT#, insurance, contact info
- FR-2: System stores truck definitions with equipment type, weight limits, location, rate floor
- FR-3: System stores preferred lanes per truck with priority weighting
- FR-4: Mock data service generates realistic Southeast US load data
- FR-5: Search endpoint filters loads by equipment type, location radius, and weight capacity
- FR-6: Scoring service ranks loads on a 0-100 scale using rate, deadhead, and lane preference
- FR-7: Web dashboard allows carrier/truck setup without API tools
- FR-8: Web dashboard displays scored/ranked search results in a table
- FR-9: Mock data service interface matches what a real DAT API adapter would use (swap-ready)

## Non-Goals (Out of Scope for MVP)

- No real DAT or Truckstop API integration (mock data only)
- No automated bidding or rate negotiation
- No carrier packet submission
- No broker communication or email
- No authentication or multi-user support
- No real-time load updates or webhooks
- No mobile app
- No payment or invoicing

## Technical Considerations

- **Stack:** Python 3.11+, FastAPI, SQLAlchemy (async), Alembic, PostgreSQL
- **Mock data:** Haversine formula for distance calculations (deadhead miles)
- **Architecture:** Service layer pattern — routes call services, services call data layer. This keeps the mock DAT service swappable with a real one.
- **No heavy frontend framework** — plain HTML + vanilla JS + simple CSS. Keeps it beginner-friendly and avoids build tooling.

## Success Metrics

- Carrier can set up profile and truck in under 2 minutes via the web UI
- Load search returns scored results in under 2 seconds
- Top-scored loads align with preferred lanes and rate floor
- Swapping mock service for real DAT API requires changing only one file

## Open Questions

- What DAT API tier/plan will be needed? (affects rate limits and available endpoints)
- Should we add Truckstop.com as a second data source in a follow-up phase?
- Will we need driver HOS tracking to validate load feasibility?
