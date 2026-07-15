import os
import requests

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


# =====================================================
# GEOCODING HELPER
# =====================================================

def _geocode_address(address_query: str) -> dict:
    """
    Geocodes a free-text address string via Google's Geocoding API.
    Works globally — handles US ZIP codes, Indian PIN codes, city names,
    states/provinces/regions, in any combination.

    Returns {"lat": ..., "lng": ..., "country": ...} or None if no match.
    """
    try:
        response = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": address_query, "key": GOOGLE_MAPS_API_KEY},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if not results:
            return None

        loc = results[0]["geometry"]["location"]
        components = results[0].get("address_components", [])
        country = next(
            (c["short_name"] for c in components if "country" in c.get("types", [])),
            "US"
        )
        return {"lat": loc["lat"], "lng": loc["lng"], "country": country}

    except Exception as e:
        print(f"[location] Geocoding failed for '{address_query}': {e}")
        return None


# =====================================================
# USER LOCATION
# =====================================================

def get_user_location(user_lat: float = None, user_lng: float = None,
                       manual_city: str = None, manual_state: str = None,
                       manual_postal_code: str = None) -> dict:
    """
    Returns user location, in priority order:
      1. Browser GPS coordinates (most accurate — reverse geocoded for city/state)
      2. Manual postal/ZIP/PIN code (+ optional city/state for disambiguation) —
         much more precise than city/state alone, since it pinpoints a
         specific area rather than an entire city's centroid
      3. Manual city/state only (least precise — resolves to city centroid,
         which may be far from the user's actual location within a large city)
      4. Hard fallback to Saint Louis, MO

    NOTE: IP-based geolocation was intentionally removed — on cloud-hosted
    backends it resolves to the SERVER's location, not the user's (e.g.
    always returning Singapore when hosted on Alibaba Cloud FC there).
    """

    # ── 1. Browser GPS (most accurate) ──
    if user_lat is not None and user_lng is not None:
        try:
            response = requests.get(
                f"https://nominatim.openstreetmap.org/reverse"
                f"?lat={user_lat}&lon={user_lng}&format=json",
                headers={"User-Agent": "SmartCartAI/1.0"},
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            addr = data.get("address", {})
            return {
                "lat":     user_lat,
                "lng":     user_lng,
                "city":    addr.get("city") or addr.get("town") or addr.get("village") or "Unknown",
                "region":  addr.get("state", "Unknown"),
                "country": addr.get("country_code", "US").upper(),
            }
        except Exception as e:
            print(f"[location] Reverse geocode failed: {e}. Falling through to manual entry.")

    # ── 2. Manual postal/ZIP/PIN code (most precise manual option) ──
    if manual_postal_code and manual_postal_code.strip():
        query_parts = [manual_postal_code.strip()]
        if manual_city:
            query_parts.append(manual_city.strip())
        if manual_state:
            query_parts.append(manual_state.strip())
        query = ", ".join(query_parts)

        geo = _geocode_address(query)
        if geo:
            return {
                "lat":     geo["lat"],
                "lng":     geo["lng"],
                "city":    manual_city or "",
                "region":  manual_state or "",
                "country": geo["country"],
            }
        print(f"[location] Postal code geocode failed for '{query}'. Falling through to city/state.")

    # ── 3. Manual city/state only (less precise — city centroid) ──
    if manual_city and manual_state:
        query = f"{manual_city.strip()}, {manual_state.strip()}"
        geo = _geocode_address(query)
        if geo:
            return {
                "lat":     geo["lat"],
                "lng":     geo["lng"],
                "city":    manual_city.strip(),
                "region":  manual_state.strip(),
                "country": geo["country"],
            }
        print(f"[location] City/state geocode failed for '{query}'. Using hard fallback.")

    # ── 4. Hard fallback ──
    print("[location] No location available (GPS denied, no manual entry). Using default.")
    return {
        "lat": 38.6270, "lng": -90.1994,
        "city": "Saint Louis", "region": "Missouri", "country": "US",
    }


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":
    import json
    print("With postal code:")
    print(json.dumps(get_user_location(manual_city="Hyderabad", manual_state="Telangana", manual_postal_code="500001"), indent=2))
    print("\nCity/state only:")
    print(json.dumps(get_user_location(manual_city="Austin", manual_state="Texas"), indent=2))
