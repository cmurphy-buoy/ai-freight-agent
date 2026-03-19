"""
Mock Truckstop.com Load Board Service.

Same pattern as MockDATService — generates fake loads from a different
"source" so the demo shows loads from multiple boards side by side.

Truckstop loads use different brokers and slightly different rate ranges
to make the demo feel realistic. In production, swap with RealTruckstopService.
"""

import random
from datetime import date, timedelta

from app.services.geo import haversine_miles
from app.services.mock_dat import CITIES, EQUIPMENT_TYPES


# Different broker names than DAT to show variety
TRUCKSTOP_BROKERS = [
    "Total Quality Logistics", "Convoy Freight", "Uber Freight",
    "RXO Brokerage", "Transplace", "Mode Transportation",
    "Redwood Logistics", "Green Mountain Logistics", "Spot Freight",
    "Edge Logistics", "BNSF Logistics", "Sunset Transportation",
]


def _generate_mc() -> str:
    return str(random.randint(200000, 899999))


def _generate_truckstop_loads(count: int = 45) -> list[dict]:
    """
    Generate mock Truckstop.com loads.

    Slightly different characteristics than DAT:
    - Truckstop tends to have more reefer and flatbed loads
    - Rate ranges skew slightly higher
    - Different broker pool
    """
    loads = []
    today = date.today()

    for i in range(count):
        origin = random.choice(CITIES)
        dest = random.choice([c for c in CITIES if c[0] != origin[0]])

        miles = haversine_miles(origin[2], origin[3], dest[2], dest[3])
        if miles < 50:
            miles = random.uniform(100, 300)
        miles = round(miles)

        # Truckstop has more reefer/flatbed representation
        equip_weights = [0.35, 0.30, 0.20, 0.10, 0.05]
        equipment = random.choices(EQUIPMENT_TYPES, weights=equip_weights, k=1)[0]

        # Truckstop rates tend slightly higher
        base_rpm = {
            "dry_van": random.uniform(1.90, 3.40),
            "reefer": random.uniform(2.40, 4.00),
            "flatbed": random.uniform(2.60, 4.20),
            "step_deck": random.uniform(2.70, 4.10),
            "power_only": random.uniform(1.60, 2.90),
        }
        rpm = round(base_rpm[equipment], 2)
        rate_total = round(rpm * miles, 2)

        weight_ranges = {
            "dry_van": (10000, 44000),
            "reefer": (8000, 42000),
            "flatbed": (15000, 48000),
            "step_deck": (20000, 47000),
            "power_only": (0, 0),
        }
        w_min, w_max = weight_ranges[equipment]
        weight = random.randint(w_min, w_max) if w_max > 0 else 0

        pickup_offset = random.randint(1, 6)
        delivery_offset = pickup_offset + max(1, miles // 500) + random.randint(0, 2)

        broker = random.choice(TRUCKSTOP_BROKERS)

        loads.append({
            "load_id": f"TS-{200000 + i}",
            "source": "Truckstop",
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


class MockTruckstopService:
    """
    Simulates the Truckstop.com load board API.
    Same interface as MockDATService — swap pattern.
    """

    def __init__(self, seed: int | None = 99):
        if seed is not None:
            random.seed(seed)
        self._loads = _generate_truckstop_loads()
        random.seed()

    def search_loads(
        self,
        equipment_type: str,
        origin_lat: float,
        origin_lng: float,
        radius_miles: int,
    ) -> list[dict]:
        results = []
        for load in self._loads:
            if load["equipment_type"] != equipment_type:
                continue
            deadhead = haversine_miles(
                origin_lat, origin_lng,
                load["origin_lat"], load["origin_lng"]
            )
            if deadhead > radius_miles:
                continue
            result = {**load, "deadhead_miles": round(deadhead, 1)}
            results.append(result)
        return results

    def get_all_loads(self) -> list[dict]:
        return self._loads
