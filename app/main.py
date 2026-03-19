"""
Main application entry point.

This is where the FastAPI app is created and all the routes are connected.
Run the app with: uvicorn app.main:app --reload

--reload means the server restarts automatically when you change code (great for development).
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routes.health import router as health_router
from app.routes.carriers import router as carriers_router
from app.routes.trucks import router as trucks_router
from app.routes.loads import router as loads_router
from app.routes.invoices import router as invoices_router
from app.routes.bank import router as bank_router
from app.routes.dispatch import router as dispatch_router
from app.routes.reports import router as reports_router

# Create the app
app = FastAPI(
    title="AI Freight Agent",
    description="Find and score freight loads based on your truck parameters",
    version="0.1.0",
)

# Resolve paths relative to this file so it works in both local dev and Vercel
_BASE_DIR = Path(__file__).resolve().parent
_STATIC_DIR = _BASE_DIR / "static"

# Mount static files (for the dashboard HTML/CSS/JS later)
if _STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# Connect route modules to the app
# Each router handles a group of related endpoints
app.include_router(health_router, tags=["health"])
app.include_router(carriers_router)
app.include_router(trucks_router)
app.include_router(loads_router)
app.include_router(invoices_router)
app.include_router(bank_router)
app.include_router(dispatch_router)
app.include_router(reports_router)


@app.get("/")
async def root():
    """Serve the main dashboard."""
    return FileResponse(str(_STATIC_DIR / "dashboard.html"))


@app.get("/dashboard")
async def dashboard():
    """Alias for the dashboard page."""
    return FileResponse(str(_STATIC_DIR / "dashboard.html"))
