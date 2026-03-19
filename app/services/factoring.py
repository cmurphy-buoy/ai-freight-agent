FACTORING_COMPANIES = {
    "rts": {"name": "RTS Financial", "advance_rate": 0.97, "fee_rate": 0.03},
    "triumph": {"name": "Triumph Pay", "advance_rate": 0.95, "fee_rate": 0.05},
    "otr": {"name": "OTR Solutions", "advance_rate": 0.96, "fee_rate": 0.04},
}


class MockFactoringService:
    """
    Simulates factoring company API. Same swap pattern as MockDATService.
    """

    def submit_invoice(self, company_key: str, invoice_amount: float) -> dict:
        company = FACTORING_COMPANIES.get(company_key)
        if not company:
            raise ValueError(f"Unknown factoring company: {company_key}")

        advance = round(invoice_amount * company["advance_rate"], 2)
        fee = round(invoice_amount * company["fee_rate"], 2)

        return {
            "factoring_company": company["name"],
            "original_amount": invoice_amount,
            "advance_amount": advance,
            "factoring_fee": fee,
            "status": "approved",
            "confirmation_number": f"FCT-{company_key.upper()}-{hash(str(invoice_amount)) % 100000:05d}",
        }

    def get_companies(self) -> list[dict]:
        return [
            {"key": k, "name": v["name"], "advance_rate": v["advance_rate"], "fee_rate": v["fee_rate"]}
            for k, v in FACTORING_COMPANIES.items()
        ]
