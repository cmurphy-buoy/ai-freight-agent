import io
import pytest


@pytest.mark.asyncio
async def test_plaid_link(client, carrier):
    resp = await client.post("/api/bank-connections/plaid/link", json={
        "carrier_id": carrier.id,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["institution_name"] == "First National Bank"
    assert data["connection_type"] == "plaid"


@pytest.mark.asyncio
async def test_list_bank_connections(client, carrier, bank_connection):
    resp = await client.get(f"/api/bank-connections?carrier_id={carrier.id}")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_delete_bank_connection(client, bank_connection):
    resp = await client.delete(f"/api/bank-connections/{bank_connection.id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_sync_transactions(client, bank_connection):
    resp = await client.post(f"/api/bank-connections/{bank_connection.id}/sync")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    amounts = [float(t["amount"]) for t in data]
    assert any(a > 0 for a in amounts)
    assert any(a < 0 for a in amounts)


@pytest.mark.asyncio
async def test_csv_upload(client, carrier):
    csv_content = "Date,Description,Amount\n2026-03-01,PILOT FUEL,-250.00\n2026-03-02,DEPOSIT BROKER,1500.00\n"
    resp = await client.post(
        f"/api/bank-connections/upload?carrier_id={carrier.id}",
        files={"file": ("statement.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 2
    assert data["skipped"] == 0


@pytest.mark.asyncio
async def test_csv_upload_dedup(client, carrier):
    csv_content = "Date,Description,Amount\n2026-03-01,SAME TXN,100.00\n"
    await client.post(
        f"/api/bank-connections/upload?carrier_id={carrier.id}",
        files={"file": ("s.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    resp = await client.post(
        f"/api/bank-connections/upload?carrier_id={carrier.id}",
        files={"file": ("s.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.json()["skipped"] == 1
    assert resp.json()["imported"] == 0


@pytest.mark.asyncio
async def test_csv_upload_bad_format(client, carrier):
    csv_content = "Foo,Bar,Baz\n1,2,3\n"
    resp = await client.post(
        f"/api/bank-connections/upload?carrier_id={carrier.id}",
        files={"file": ("bad.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    assert resp.status_code == 400
