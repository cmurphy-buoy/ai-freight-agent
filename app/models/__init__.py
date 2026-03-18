"""
Models package.

Import Base here so Alembic can find all models by importing this one package.
As you add new models (CarrierProfile, Truck, etc.), import them here too
so Alembic's auto-generate picks them up.
"""

from app.models.base import Base
from app.models.carrier import CarrierProfile
from app.models.truck import Truck, PreferredLane, EquipmentType
from app.models.invoice import Invoice, InvoiceStatus

__all__ = ["Base", "CarrierProfile", "Truck", "PreferredLane", "EquipmentType", "Invoice", "InvoiceStatus"]
