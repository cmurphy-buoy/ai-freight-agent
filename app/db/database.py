"""
Database connection setup.

This file creates the "engine" (the connection to PostgreSQL) and the
"session" (how the app talks to the database for each request).

KEY CONCEPTS FOR BEGINNERS:
- Engine: Like opening a phone line to the database
- Session: Like an individual phone call — you open one, do your work, then hang up
- AsyncSession: Same thing but non-blocking (the app can do other stuff while waiting)
"""

from __future__ import annotations

from fastapi import HTTPException
from app.config import settings

# Create the engine — this is the connection pool to PostgreSQL
# Only connect if DATABASE_URL is configured (allows app to boot without a DB for demo/preview)
engine = None
async_session = None

if settings.has_database:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(
        settings.database_url,
        echo=False,  # Set to True if you want to see every SQL query in the terminal (noisy but helpful for debugging)
    )

    # Session factory — creates a new session each time we need to talk to the DB
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Keeps data accessible after committing (saves extra DB calls)
    )


async def get_db():
    """
    Dependency that FastAPI uses to give each request its own database session.

    How it works:
    1. Opens a session (starts the "phone call")
    2. Yields it to the route handler (your code uses it)
    3. Closes it when the request is done (hangs up)

    You'll see this used like: async def my_route(db: AsyncSession = Depends(get_db))
    """
    if async_session is None:
        raise HTTPException(
            status_code=503,
            detail="Database not configured. Set DATABASE_URL environment variable.",
        )
    async with async_session() as session:
        yield session
