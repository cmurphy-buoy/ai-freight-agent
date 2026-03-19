"""
Geographic utility functions.

The Haversine formula calculates the distance between two points on Earth
using their latitude and longitude. We use this to figure out how far
a truck is from a load's pickup point (deadhead miles).

BEGINNER NOTE:
- Latitude = how far north/south (Atlanta is ~33.7)
- Longitude = how far east/west (Atlanta is ~-84.4)
- The formula accounts for Earth being round, not flat
"""

import math


def haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the distance in miles between two lat/lng points.

    Example:
        haversine_miles(33.749, -84.388, 32.776, -96.797)
        # Atlanta to Dallas ≈ 725 miles
    """
    R = 3958.8  # Earth's radius in miles

    # Convert degrees to radians (the math functions need radians)
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    # Haversine formula
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(R * c, 1)
