"""
Health check route.

This is a simple endpoint that returns {"status": "ok"}.
Used to verify the server is running — monitoring tools, load balancers,
and you can hit it in your browser to make sure things are alive.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Returns ok if the server is running."""
    return {"status": "ok"}
