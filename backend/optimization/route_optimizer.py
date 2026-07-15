from backend.services.store_finder import haversine_distance


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

    remaining = stores.copy()

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