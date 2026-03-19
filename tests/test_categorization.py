from datetime import date
from decimal import Decimal

import pytest

from app.models.bank import BankTransaction
from app.services.categorization import TransactionCategorizationService


@pytest.mark.asyncio
async def test_categorize_fuel(db, bank_connection):
    txn = BankTransaction(
        bank_connection_id=bank_connection.id,
        transaction_id="cat-fuel-1",
        date=date.today(),
        description="PILOT TRAVEL CENTER #4521",
        amount=Decimal("-350.00"),
        is_deposit=False,
    )
    db.add(txn)
    await db.commit()

    service = TransactionCategorizationService(db)
    result = await service.categorize(bank_connection.id)
    assert result["by_category"].get("fuel", 0) >= 1


@pytest.mark.asyncio
async def test_categorize_tolls(db, bank_connection):
    txn = BankTransaction(
        bank_connection_id=bank_connection.id,
        transaction_id="cat-toll-1",
        date=date.today(),
        description="EZ PASS REPLENISH",
        amount=Decimal("-50.00"),
        is_deposit=False,
    )
    db.add(txn)
    await db.commit()

    service = TransactionCategorizationService(db)
    result = await service.categorize(bank_connection.id)
    assert result["by_category"].get("tolls", 0) >= 1


@pytest.mark.asyncio
async def test_categorize_does_not_overwrite(db, bank_connection):
    txn = BankTransaction(
        bank_connection_id=bank_connection.id,
        transaction_id="cat-existing-1",
        date=date.today(),
        description="PILOT FUEL",
        amount=Decimal("-100.00"),
        is_deposit=False,
        category="manual_override",
    )
    db.add(txn)
    await db.commit()

    service = TransactionCategorizationService(db)
    result = await service.categorize(bank_connection.id)
    await db.refresh(txn)
    assert txn.category == "manual_override"


@pytest.mark.asyncio
async def test_categorize_other_default(db, bank_connection):
    txn = BankTransaction(
        bank_connection_id=bank_connection.id,
        transaction_id="cat-other-1",
        date=date.today(),
        description="RANDOM UNKNOWN PURCHASE",
        amount=Decimal("-25.00"),
        is_deposit=False,
    )
    db.add(txn)
    await db.commit()

    service = TransactionCategorizationService(db)
    result = await service.categorize(bank_connection.id)
    assert result["by_category"].get("other", 0) >= 1
