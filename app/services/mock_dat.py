"""
Mock DAT Load Board Service.

This generates fake-but-realistic load listings so you can build and test
the entire search/score/display pipeline WITHOUT needing a real DAT API key.

IMPORTANT DESIGN DECISION:
This class follows the same interface a real DAT API adapter would use:
    search_loads(equipment_type, origin_lat, origin_lng, radius_miles) -> list[dict]

When you get real API access, you create a RealDATService with the same method
signature, swap it in, and everything else keeps working.

BEGINNER NOTE:
- Each "load" is a shipping job: pick up cargo at point A, deliver to point B
- Brokers post loads, carriers (you) search for them and bid
- Rate per mile = how much you get paid for each mile driven
"""

import random
from datetime import date, timedelta

from app.services.geo import haversine_miles


# Realistic cities with coordinates — Southeast US focus
CITIES = [
    ("Atlanta", "GA", 33.749, -84.388),
    ("Dallas", "TX", 32.776, -96.797),
    ("Houston", "TX", 29.760, -95.370),
    ("Nashville", "TN", 36.162, -86.781),
    ("Charlotte", "NC", 35.227, -80.843),
    ("Jacksonville", "FL", 30.332, -81.656),
    ("Memphis", "TN", 35.150, -90.049),
    ("Birmingham", "AL", 33.521, -86.802),
    ("New Orleans", "LA", 29.951, -90.072),
    ("Savannah", "GA", 32.081, -81.091),
    ("Raleigh", "NC", 35.780, -78.639),
    ("Tampa", "FL", 27.951, -82.458),
    ("Miami", "FL", 25.762, -80.192),
    ("Louisville", "KY", 38.253, -85.759),
    ("Knoxville", "TN", 35.961, -83.921),
    ("Columbia", "SC", 34.000, -81.035),
    ("Mobile", "AL", 30.695, -88.040),
    ("Chattanooga", "TN", 35.046, -85.309),
    ("Little Rock", "AR", 34.746, -92.290),
    ("San Antonio", "TX", 29.425, -98.495),
    ("Greenville", "SC", 34.852, -82.394),
    ("Augusta", "GA", 33.474, -81.975),
    ("Macon", "GA", 32.837, -83.632),
    ("Montgomery", "AL", 32.367, -86.300),
    ("Shreveport", "LA", 32.525, -93.750),
    ("Baton Rouge", "LA", 30.451, -91.187),
    ("Richmond", "VA", 37.541, -77.436),
    ("Norfolk", "VA", 36.851, -76.286),
    ("Pensacola", "FL", 30.443, -87.217),
    ("Orlando", "FL", 28.538, -81.379),
]

BROKER_NAMES = [
    "Apex Freight", "TQL Logistics", "CH Robinson", "Echo Global",
    "XPO Logistics", "Coyote Logistics", "JB Hunt Brokerage", "Schneider Freight",
    "GlobalTranz", "Arrive Logistics", "Nolan Transport", "FreightWise",
    "RXO Brokerage", "Landstar System", "Werner Logistics",
]

EQUIPMENT_TYPES = ["dry_van", "reefer", "flatbed", "step_deck", "power_only"]


def _generate_mc() -> str:
    """Generate a random 6-digit MC number for a broker."""
    return str(random.randint(100000, 999999))


def _generate_loads(count: int = 65) -> list[dict]:
    """
    Generate a list of realistic mock loads.

    Each load has:
    - Origin and destination (different cities)
    - Equipment type, weight, mileage
    - Rate (total and per mile)
    - Pickup/delivery dates in the next 1-7 days
    - Broker info
    """
    loads = []
    today = date.today()

    for i in range(count):
        # Pick two different cities
        origin = random.choice(CITIES)
        dest = random.choice([c for c in CITIES if c[0] != origin[0]])

        # Calculate actual miles between the two cities
        miles = haversine_miles(origin[2], origin[3], dest[2], dest[3])
        if miles < 50:
            miles = random.uniform(100, 300)  # minimum viable load distance
        miles = round(miles)

        # Equipment type — weighted toward dry van (most common)
        equip_weights = [0.45, 0.25, 0.15, 0.10, 0.05]
        equipment = random.choices(EQUIPMENT_TYPES, weights=equip_weights, k=1)[0]

        # Rate per mile varies by equipment and distance
        base_rpm = {
            "dry_van": random.uniform(1.80, 3.20),
            "reefer": random.uniform(2.20, 3.80),
            "flatbed": random.uniform(2.50, 4.00),
            "step_deck": random.uniform(2.60, 3.90),
            "power_only": random.uniform(1.50, 2.80),
        }
        rpm = round(base_rpm[equipment], 2)
        rate_total = round(rpm * miles, 2)

        # Weight varies by equipment
        weight_ranges = {
            "dry_van": (10000, 44000),
            "reefer": (8000, 42000),
            "flatbed": (15000, 48000),
            "step_deck": (20000, 47000),
            "power_only": (0, 0),
        }
        w_min, w_max = weight_ranges[equipment]
        weight = random.randint(w_min, w_max) if w_max > 0 else 0

        # Dates
        pickup_offset = random.randint(1, 5)
        delivery_offset = pickup_offset + max(1, miles // 500) + random.randint(0, 2)

        broker = random.choice(BROKER_NAMES)

        loads.append({
            "load_id": f"DAT-{100000 + i}",
            "source": "DAT",
            "origin_city": origin[0],
            "origin_state": origin[1],
            "origin_lat": origin[2],
            "origin_lng": origin[3],
            "destination_city": dest[0],
            "destination_state": dest[1],
            "dest_lat": dest[2],
            "dest_lng": dest[3],
            "equipment_type": equipment,
            "weight_lbs": weight,
            "rate_total": rate_total,
            "rate_per_mile": rpm,
            "miles": miles,
            "pickup_date": str(today + timedelta(days=pickup_offset)),
            "delivery_date": str(today + timedelta(days=delivery_offset)),
            "broker_name": broker,
            "broker_mc": _generate_mc(),
        })

    return loads


class MockDATService:
    """
    Simulates the DAT load board API.

    Usage:
        service = MockDATService()
        loads = service.search_loads("dry_van", 33.749, -84.388, 200)
        # Returns loads with dry van equipment within 200 miles of Atlanta
    """

    def __init__(self, seed: int | None = 42):
        """
        seed: Makes the random data repeatable. Same seed = same loads every time.
              Set to None for truly random data each time.
        """
        if seed is not None:
            random.seed(seed)
        self._loads = _generate_loads()
        # Reset seed so other random calls aren't affected
        random.seed()

    def search_loads(
        self,
        equipment_type: str,
        origin_lat: float,
        origin_lng: float,
        radius_miles: int,
    ) -> list[dict]:
        """
        Search for loads matching criteria.

        Args:
            equipment_type: "dry_van", "reefer", "flatbed", "step_deck", or "power_only"
            origin_lat: Truck's current latitude
            origin_lng: Truck's current longitude
            radius_miles: How far from the truck to search (deadhead radius)

        Returns:
            List of load dicts that match, each with an added "deadhead_miles" field
        """
        results = []

        for load in self._loads:
            # Must match equipment type
            if load["equipment_type"] != equipment_type:
                continue

            # Calculate how far the truck would drive empty to reach this load's pickup
            deadhead = haversine_miles(
                origin_lat, origin_lng,
                load["origin_lat"], load["origin_lng"]
            )

            # Must be within the search radius
            if deadhead > radius_miles:
                continue

            # Add deadhead to the result
            result = {**load, "deadhead_miles": round(deadhead, 1)}
            results.append(result)

        return results

    def get_all_loads(self) -> list[dict]:
        """Return all mock loads (useful for debugging)."""
        return self._loads
