import math


def haversine_distance(lat1, lng1, lat2, lng2):
    """Return approximate distance in kilometers between two coordinate pairs."""
    radius_km = 6371
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def optimize_route(stores, user_location):
    if not stores:
        return []

    valid_stores = [
        s for s in stores
        if s and s.get("lat") and s.get("lng")
    ]

    if not valid_stores:
        return []

    """
    Simple nearest-neighbor route optimization
    """

    remaining = valid_stores.copy()

    route = []

    current_lat = user_location["lat"]
    current_lng = user_location["lng"]

    while remaining:

        nearest_store = min(

            remaining,

            key=lambda s: haversine_distance(
                current_lat,
                current_lng,
                s["lat"],
                s["lng"]
            )
        )

        route.append(nearest_store)

        current_lat = nearest_store["lat"]
        current_lng = nearest_store["lng"]

        remaining.remove(nearest_store)

    return route
