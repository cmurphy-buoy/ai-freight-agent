import pytest
from datetime import date, timedelta


@pytest.mark.asyncio
async def test_create_invoice(client, carrier):
    resp = await client.post("/api/invoices", json={
        "carrier_id": carrier.id,
        "broker_name": "Test Broker",
        "broker_mc": "123456",
        "origin_city": "Atlanta",
        "origin_state": "GA",
        "destination_city": "Dallas",
        "destination_state": "TX",
        "amount": 2000.00,
        "rate_per_mile": 2.50,
        "miles": 800,
        "due_date": str(date.today() + timedelta(days=30)),
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["broker_name"] == "Test Broker"
    assert data["status"] == "draft"
    assert data["invoice_date"] == str(date.today())


@pytest.mark.asyncio
async def test_create_invoice_from_load(client, carrier):
    resp = await client.post("/api/invoices/from-load", json={
        "carrier_id": carrier.id,
        "broker_name": "Load Broker",
        "broker_mc": "654321",
        "origin_city": "Nashville",
        "origin_state": "TN",
        "destination_city": "Miami",
        "destination_state": "FL",
        "rate_total": 3000.00,
        "rate_per_mile": 3.00,
        "miles": 1000,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["amount"] == "3000.00"
    assert data["status"] == "draft"
    assert data["due_date"] == str(date.today() + timedelta(days=30))


@pytest.mark.asyncio
async def test_get_invoice(client, sample_invoice):
    resp = await client.get(f"/api/invoices/{sample_invoice.id}")
    assert resp.status_code == 200
    assert resp.json()["broker_name"] == "Apex Freight"


@pytest.mark.asyncio
async def test_get_invoice_not_found(client):
    resp = await client.get("/api/invoices/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_invoice_status(client, sample_invoice):
    resp = await client.put(f"/api/invoices/{sample_invoice.id}", json={
        "status": "paid",
        "payment_date": str(date.today()),
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "paid"


@pytest.mark.asyncio
async def test_list_invoices_filter_status(client, carrier, sample_invoice):
    resp = await client.get(f"/api/invoices?carrier_id={carrier.id}&status=outstanding")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert all(inv["status"] == "outstanding" for inv in data)


@pytest.mark.asyncio
async def test_create_invoice_invalid_carrier(client):
    resp = await client.post("/api/invoices", json={
        "carrier_id": 99999,
        "broker_name": "Bad",
        "broker_mc": "111111",
        "origin_city": "A",
        "origin_state": "GA",
        "destination_city": "B",
        "destination_state": "TX",
        "amount": 100,
        "rate_per_mile": 1,
        "miles": 100,
        "due_date": str(date.today()),
    })
    assert resp.status_code == 400
