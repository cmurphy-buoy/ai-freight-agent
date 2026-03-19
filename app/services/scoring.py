"""
Load Scoring Service.

Takes a list of loads and scores each one 0-100 based on how good it is
for YOUR specific truck. Higher score = better load for you.

SCORING BREAKDOWN (100 points total):
- Rate per mile:    0-40 points (higher rate = more points)
- Deadhead miles:   0-30 points (shorter deadhead = more points)
- Preferred lane:   0-30 points (bonus if the route matches a saved lane)

BEGINNER NOTE:
Think of it like a grade. A load scoring 85 is an "A" — great rate,
close to your truck, and on a route you like. A load scoring 35 is a "D" —
maybe the rate is ok but it's far away and going somewhere you don't want to be.
"""

from decimal import Decimal


class LoadScoringService:
    """
    Scores and ranks loads for a specific truck.

    Usage:
        scorer = LoadScoringService(
            min_rate=Decimal("2.50"),
            max_deadhead=150,
            preferred_lanes=[
                {"origin_city": "Atlanta", "origin_state": "GA",
                 "destination_city": "Dallas", "destination_state": "TX",
                 "priority_weight": 8}
            ]
        )
        scored = scorer.score_loads(loads)
        # Returns loads sorted by score descending, with score + breakdown
    """

    def __init__(
        self,
        min_rate: Decimal,
        max_deadhead: int,
        preferred_lanes: list[dict],
    ):
        self.min_rate = float(min_rate)
        self.max_deadhead = max_deadhead
        self.preferred_lanes = preferred_lanes

    def _rate_score(self, rate_per_mile: float) -> float:
        """
        Score based on rate per mile. 0-40 points.

        - At or below min_rate: 0 points
        - At $1.00 above min_rate: 40 points (max)
        - Linear scale in between
        """
        if rate_per_mile <= self.min_rate:
            return 0.0

        # How much above your minimum is this rate?
        above_min = rate_per_mile - self.min_rate

        # $1.00 above minimum = max score. Scale linearly.
        score = min(above_min / 1.0, 1.0) * 40.0
        return round(score, 1)

    def _deadhead_score(self, deadhead_miles: float) -> float:
        """
        Score based on deadhead distance. 0-30 points.

        - 0 miles deadhead: 30 points (perfect — load is right where you are)
        - At max_deadhead: 0 points
        - Linear scale in between
        """
        if deadhead_miles >= self.max_deadhead:
            return 0.0

        # Closer = better. Invert the ratio.
        ratio = 1.0 - (deadhead_miles / self.max_deadhead)
        return round(ratio * 30.0, 1)

    def _lane_score(self, load: dict) -> float:
        """
        Score based on preferred lane match. 0-30 points.

        Checks if the load's origin→destination matches any of your saved lanes.
        If it matches, points scale with the lane's priority_weight (1-10).

        - No match: 0 points
        - Match with priority 10: 30 points
        - Match with priority 5: 15 points
        """
        load_origin = (load["origin_city"].lower(), load["origin_state"].lower())
        load_dest = (load["destination_city"].lower(), load["destination_state"].lower())

        best_score = 0.0

        for lane in self.preferred_lanes:
            lane_origin = (lane["origin_city"].lower(), lane["origin_state"].lower())
            lane_dest = (lane["destination_city"].lower(), lane["destination_state"].lower())

            if load_origin == lane_origin and load_dest == lane_dest:
                # Full match — scale by priority weight
                score = (lane["priority_weight"] / 10.0) * 30.0
                best_score = max(best_score, score)

            elif load_origin == lane_origin or load_dest == lane_dest:
                # Partial match (same origin OR same destination) — half credit
                score = (lane["priority_weight"] / 10.0) * 15.0
                best_score = max(best_score, score)

        return round(best_score, 1)

    def score_loads(self, loads: list[dict]) -> list[dict]:
        """
        Score each load, filter out below-minimum-rate loads,
        and return sorted by score (best first).

        Each load gets added fields:
        - score: int (0-100)
        - score_breakdown: {rate_points, deadhead_points, lane_points}
        """
        scored = []

        for load in loads:
            rpm = load["rate_per_mile"]

            # Skip loads below rate floor
            if rpm < self.min_rate:
                continue

            rate_pts = self._rate_score(rpm)
            deadhead_pts = self._deadhead_score(load["deadhead_miles"])
            lane_pts = self._lane_score(load)

            total = round(rate_pts + deadhead_pts + lane_pts)

            scored.append({
                **load,
                "score": min(total, 100),
                "score_breakdown": {
                    "rate_points": rate_pts,
                    "deadhead_points": deadhead_pts,
                    "lane_points": lane_pts,
                },
            })

        # Sort by score descending (best loads first)
        scored.sort(key=lambda x: x["score"], reverse=True)

        return scored
