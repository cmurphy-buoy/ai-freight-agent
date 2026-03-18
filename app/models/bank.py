import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Integer,
    JSON, Numeric, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ConnectionType(str, enum.Enum):
    plaid = "plaid"
    manual = "manual"


class BankConnection(Base):
    __tablename__ = "bank_connections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey("carrier_profiles.id"), nullable=False)
    institution_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_mask: Mapped[str] = mapped_column(String(4), nullable=False)
    connection_type: Mapped[ConnectionType] = mapped_column(Enum(ConnectionType), nullable=False)
    plaid_access_token: Mapped[str | None] = mapped_column(String(200), nullable=True)
    plaid_item_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    carrier: Mapped["CarrierProfile"] = relationship("CarrierProfile")
    transactions: Mapped[list["BankTransaction"]] = relationship(
        "BankTransaction", back_populates="bank_connection", cascade="all, delete-orphan"
    )


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bank_connection_id: Mapped[int] = mapped_column(ForeignKey("bank_connections.id"), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_deposit: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    matched_invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    bank_connection: Mapped["BankConnection"] = relationship("BankConnection", back_populates="transactions")
    matched_invoice: Mapped["Invoice | None"] = relationship("Invoice")
