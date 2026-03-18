import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

from app.services.mock_dat import BROKER_NAMES


def _generate_transaction_id() -> str:
    return f"plaid-txn-{uuid.uuid4().hex[:12]}"


class MockPlaidService:
    """
    Simulates the Plaid API.
    Same swap pattern as MockDATService.
    """

    def __init__(self, seed: int | None = 42):
        if seed is not None:
            random.seed(seed)
        self._seed = seed

    def create_link(self, carrier_id: int) -> dict:
        return {
            "access_token": f"mock-access-{carrier_id}-{uuid.uuid4().hex[:8]}",
            "item_id": f"mock-item-{carrier_id}",
            "institution_name": "First National Bank",
            "account_name": "Business Checking",
            "account_mask": "4521",
        }

    def get_transactions(
        self, access_token: str, start_date: date, end_date: date
    ) -> list[dict]:
        if self._seed is not None:
            random.seed(self._seed)

        transactions = []
        broker_subset = random.sample(BROKER_NAMES, min(6, len(BROKER_NAMES)))

        # Clean broker deposits (exact names)
        for i, broker in enumerate(broker_subset[:3]):
            mc = str(random.randint(100000, 999999))
            txn_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
            amount = round(random.uniform(800, 4500), 2)
            transactions.append({
                "transaction_id": _generate_transaction_id(),
                "date": str(txn_date),
                "description": f"DEPOSIT - {broker} MC#{mc}",
                "amount": amount,
            })

        # Messy broker deposits (abbreviated/truncated)
        messy_formats = [
            "ACH DEPOSIT {} LOG",
            "WIRE {} FRGHT",
            "DEP {} TRANS",
            "ACH CR {}",
        ]
        for i, broker in enumerate(broker_subset[3:]):
            short_name = broker.split()[0].upper()
            txn_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
            amount = round(random.uniform(1000, 5000), 2)
            fmt = random.choice(messy_formats)
            transactions.append({
                "transaction_id": _generate_transaction_id(),
                "date": str(txn_date),
                "description": fmt.format(short_name),
                "amount": amount,
            })

        # Unmatched deposits
        unmatched_companies = ["Smith Hauling", "Quick Transport LLC", "Midwest Carriers"]
        for company in unmatched_companies:
            txn_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
            amount = round(random.uniform(500, 3000), 2)
            transactions.append({
                "transaction_id": _generate_transaction_id(),
                "date": str(txn_date),
                "description": f"ACH DEPOSIT {company.upper()}",
                "amount": amount,
            })

        # Expense transactions (negative amounts)
        expenses = [
            ("PILOT TRAVEL CENTER #4521", -random.uniform(200, 600)),
            ("LOVES COUNTRY STORE #312", -random.uniform(150, 500)),
            ("FLYING J #1892", -random.uniform(180, 450)),
            ("EZ PASS REPLENISH", -random.uniform(25, 75)),
            ("TOLLWAY AUTHORITY", -random.uniform(5, 30)),
            ("PROGRESSIVE INSURANCE PMT", -random.uniform(800, 1500)),
            ("NATIONAL INTERSTATE INS", -random.uniform(600, 1200)),
            ("PETERBILT SERVICE CTR", -random.uniform(300, 2000)),
            ("DISCOUNT TIRE #0891", -random.uniform(200, 800)),
            ("FREIGHTLINER DEALER SVC", -random.uniform(400, 1500)),
            ("LUMPER SERVICE - WAREHOUSE", -random.uniform(50, 150)),
            ("CAT SCALE #2847", -random.uniform(10, 15)),
            ("TRUCK STOP PARKING OVERNIGHT", -random.uniform(15, 30)),
            ("SAMSARA ELD MONTHLY", -random.uniform(25, 45)),
            ("MOTIVE KEEPTRUCKIN SUB", -random.uniform(20, 40)),
            ("ATM WITHDRAWAL", -random.uniform(40, 200)),
            ("WALMART SUPERCENTER", -random.uniform(20, 100)),
            ("DRIVER PAYROLL DIRECT DEP", -random.uniform(1500, 3500)),
            ("BLUE BEACON TRUCK WASH", -random.uniform(30, 75)),
            ("SPEEDWAY GAS #2941", -random.uniform(100, 350)),
            ("IPASS TOLL REPLENISH", -random.uniform(40, 100)),
            ("TA PETRO #0182", -random.uniform(200, 500)),
        ]
        for desc, amt in expenses:
            txn_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
            transactions.append({
                "transaction_id": _generate_transaction_id(),
                "date": str(txn_date),
                "description": desc,
                "amount": round(amt, 2),
            })

        random.seed()
        return sorted(transactions, key=lambda t: t["date"])
