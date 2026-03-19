from datetime import date
from decimal import Decimal

import pytest

from app.models.bank import BankTransaction
from app.services.reconciliation import ReconciliationService, _normalize_name


def test_normalize_name():
    assert _normalize_name("Apex Freight") == "apex"
    assert _normalize_name("TQL Logistics") == "tql"
    assert _normalize_name("CH Robinson Inc") == "ch robinson"
    assert _normalize_name("  Coyote  Logistics  LLC  ") == "coyote"


@pytest.mark.asyncio
async def test_reconcile_exact_match(db, carrier, sample_invoice, bank_connection):
    txn = BankTransaction(
        bank_connection_id=bank_connection.id,
        transaction_id="test-match-1",
        date=date.today(),
        description="DEPOSIT - Apex Freight MC#384291",
        amount=Decimal("2500.00"),
        is_deposit=True,
    )
    db.add(txn)
    await db.commit()

    service = ReconciliationService(db)
    result = await service.reconcile(carrier.id)

    assert result["matched_count"] == 1
    assert len(result["newly_paid_invoices"]) == 1
    assert result["newly_paid_invoices"][0]["broker_name"] == "Apex Freight"


@pytest.mark.asyncio
async def test_reconcile_within_tolerance(db, carrier, sample_invoice, bank_connection):
    txn = BankTransaction(
        bank_connection_id=bank_connection.id,
        transaction_id="test-tolerance-1",
        date=date.today(),
        description="DEPOSIT - Apex Freight",
        amount=Decimal("2500.30"),
        is_deposit=True,
    )
    db.add(txn)
    await db.commit()

    service = ReconciliationService(db)
    result = await service.reconcile(carrier.id)
    assert result["matched_count"] == 1


@pytest.mark.asyncio
async def test_reconcile_unmatched(db, carrier, sample_invoice, bank_connection):
    txn = BankTransaction(
        bank_connection_id=bank_connection.id,
        transaction_id="test-unmatched-1",
        date=date.today(),
        description="ACH DEPOSIT UNKNOWN COMPANY",
        amount=Decimal("999.00"),
        is_deposit=True,
    )
    db.add(txn)
    await db.commit()

    service = ReconciliationService(db)
    result = await service.reconcile(carrier.id)
    assert result["matched_count"] == 0
    assert len(result["unmatched_deposits"]) == 1


@pytest.mark.asyncio
async def test_reconcile_idempotent(db, carrier, sample_invoice, bank_connection):
    txn = BankTransaction(
        bank_connection_id=bank_connection.id,
        transaction_id="test-idemp-1",
        date=date.today(),
        description="DEPOSIT - Apex Freight",
        amount=Decimal("2500.00"),
        is_deposit=True,
    )
    db.add(txn)
    await db.commit()

    service = ReconciliationService(db)
    r1 = await service.reconcile(carrier.id)
    assert r1["matched_count"] == 1

    r2 = await service.reconcile(carrier.id)
    assert r2["matched_count"] == 0
