from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank import BankTransaction

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "fuel": ["pilot", "loves", "ta petro", "flying j", "fuel", "diesel", "gas"],
    "tolls": ["ez pass", "ezpass", "toll", "pike", "turnpike", "ipass"],
    "insurance": ["insurance", "progressive", "national interstate", "great west"],
    "maintenance": [
        "repair", "tire", "service", "mechanic", "parts", "shop",
        "freightliner", "peterbilt", "kenworth",
    ],
    "lumper": ["lumper", "unload"],
    "scale": ["cat scale", "scale"],
    "parking": ["truck stop", "parking", "truckpark"],
    "subscription": ["eld", "samsara", "keeptruckin", "motive", "project44"],
}


class TransactionCategorizationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def categorize(self, bank_connection_id: int) -> dict:
        result = await self.db.execute(
            select(BankTransaction).where(
                BankTransaction.bank_connection_id == bank_connection_id,
                BankTransaction.category.is_(None),
            )
        )
        transactions = list(result.scalars().all())

        counts: dict[str, int] = {}
        total = 0

        for txn in transactions:
            if txn.is_reconciled:
                txn.category = "broker_payment"
                counts["broker_payment"] = counts.get("broker_payment", 0) + 1
                total += 1
                continue

            desc_lower = txn.description.lower()
            matched_category = "other"

            for category, keywords in CATEGORY_KEYWORDS.items():
                if any(kw in desc_lower for kw in keywords):
                    matched_category = category
                    break

            txn.category = matched_category
            counts[matched_category] = counts.get(matched_category, 0) + 1
            total += 1

        await self.db.commit()

        return {
            "categorized_count": total,
            "by_category": counts,
        }
