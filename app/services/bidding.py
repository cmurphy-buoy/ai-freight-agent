from decimal import Decimal
from app.models.bid import BidStatus


class BiddingService:
    """
    Calculates bid amounts based on strategy.
    In production, this would also submit bids via broker APIs.
    """

    STRATEGIES = {
        "market": {"rate_adjustment": 0.0, "description": "Bid at listed rate"},
        "aggressive": {"rate_adjustment": -0.05, "description": "Bid 5% below listed rate"},
        "conservative": {"rate_adjustment": 0.05, "description": "Bid 5% above listed rate"},
    }

    def calculate_bid(self, listed_rate: float, miles: int, strategy: str = "market") -> dict:
        config = self.STRATEGIES.get(strategy, self.STRATEGIES["market"])
        adjustment = config["rate_adjustment"]
        bid_rate = round(listed_rate * (1 + adjustment), 2)
        bid_total = round(bid_rate * miles, 2)

        return {
            "bid_rate_per_mile": bid_rate,
            "bid_amount": bid_total,
            "strategy": strategy,
            "adjustment_pct": adjustment * 100,
        }

    def auto_bid_loads(self, scored_loads: list[dict], min_score: int = 70, strategy: str = "market", max_bids: int = 3) -> list[dict]:
        """Filter loads above min_score and calculate bids for top N."""
        qualifying = [l for l in scored_loads if l.get("score", 0) >= min_score]
        qualifying.sort(key=lambda l: l.get("score", 0), reverse=True)
        top_loads = qualifying[:max_bids]

        bids = []
        for load in top_loads:
            bid_calc = self.calculate_bid(load["rate_per_mile"], load["miles"], strategy)
            bids.append({
                **load,
                **bid_calc,
                "auto_bid": True,
            })
        return bids
