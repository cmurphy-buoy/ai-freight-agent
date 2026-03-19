import asyncio
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database import get_db
from app.main import app
from app.models.base import Base
from app.models.carrier import CarrierProfile
from app.models.invoice import Invoice, InvoiceStatus
from app.models.bank import BankConnection, BankTransaction, ConnectionType


TEST_DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/freight_agent_test"

engine = create_async_engine(TEST_DATABASE_URL)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSession() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def carrier(db):
    c = CarrierProfile(
        company_name="Test Trucking",
        mc_number="123456",
        dot_number="1234567",
        contact_name="John",
        contact_email="john@test.com",
        contact_phone="555-0100",
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@pytest_asyncio.fixture
async def sample_invoice(db, carrier):
    inv = Invoice(
        carrier_id=carrier.id,
        broker_name="Apex Freight",
        broker_mc="384291",
        origin_city="Atlanta",
        origin_state="GA",
        destination_city="Dallas",
        destination_state="TX",
        amount=Decimal("2500.00"),
        rate_per_mile=Decimal("2.50"),
        miles=1000,
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=InvoiceStatus.outstanding,
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv


@pytest_asyncio.fixture
async def bank_connection(db, carrier):
    conn = BankConnection(
        carrier_id=carrier.id,
        institution_name="First National Bank",
        account_name="Business Checking",
        account_mask="4521",
        connection_type=ConnectionType.plaid,
        plaid_access_token="mock-token",
        plaid_item_id="mock-item",
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return conn
