"""
Base model for all database tables.

Every model (CarrierProfile, Truck, etc.) will inherit from this Base class.
SQLAlchemy uses it to keep track of all your tables.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """All database models inherit from this."""
    pass
