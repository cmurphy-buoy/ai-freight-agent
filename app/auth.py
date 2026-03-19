"""
Simple token-based authentication.

Carriers get an API token when created. Pass it via X-API-Token header
or ?token= query parameter to authenticate requests.

This is optional auth — routes work without a token for backward compatibility.
"""

import secrets

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.carrier import CarrierProfile


async def get_current_carrier(
    request: Request, db: AsyncSession = Depends(get_db)
) -> CarrierProfile | None:
    """Optional auth — returns carrier if token provided, None otherwise.

    This allows the API to work both with and without auth for backward compatibility.
    """
    token = request.headers.get("X-API-Token") or request.query_params.get("token")
    if not token:
        return None
    result = await db.execute(
        select(CarrierProfile).where(CarrierProfile.api_token == token)
    )
    carrier = result.scalar_one_or_none()
    if not carrier:
        raise HTTPException(status_code=401, detail="Invalid API token")
    return carrier


def generate_api_token() -> str:
    """Generate a cryptographically secure 64-character hex token."""
    return secrets.token_hex(32)
