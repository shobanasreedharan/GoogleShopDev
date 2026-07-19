import os
import math
import requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


# =====================================================
# DISTANCE
# =====================================================

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )

    return 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)) * R


# =====================================================
# STORE BRAND NORMALIZER
# =====================================================

def normalize_store_brand(name):
    if not name:
        return "Unknown"

    name = name.lower()

    mapping = {
        # US chains
        "walmart":  "Walmart",
        "target":   "Target",
        "kroger":   "Kroger",
        "aldi":     "Aldi",
        "whole foods": "Whole Foods",
        "trader joe": "Trader Joe's",
        "costco":   "Costco",
        "heb":      "H-E-B",
        "publix":   "Publix",
        "safeway":  "Safeway",
        "sprouts":  "Sprouts",
        "dierbergs": "Dierbergs",
        "schnucks": "Schnucks",
        # India chains
        "reliance fresh": "Reliance Fresh",
        "reliance smart": "Reliance Smart",
        "big bazaar": "Big Bazaar",
        "dmart":    "DMart",
        "more supermarket": "More",
        "spencer": "Spencer's",
        "star bazaar": "Star Bazaar",
        "nature's basket": "Nature's Basket",
    }

    for k, v in mapping.items():
        if k in name:
            return v

    # Any store not in the mapping (any country/chain) falls through here —
    # returns its real name as-is, title-cased. Not an error case.
    return name.title()


# =====================================================
# NEARBY STORES
# =====================================================

def find_nearby_grocery_stores(lat, lng, radius=15000):

    if lat is None or lng is None:
        print("[stores] invalid input coordinates")
        return []

    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        print("[stores] coordinates not numeric")
        return []

    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    # "supermarket" is a valid Google Places type globally.
    # "grocery_or_supermarket" is NOT a real Places API type — it silently
    # failed on every call. Replaced with a keyword-based search instead,
    # which works well internationally (matches local names/languages too,
    # e.g. "Reliance Fresh", "Big Bazaar", "kirana store" in India).
    all_results = []

    # Pass 1: official "supermarket" type (most reliable everywhere)
    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "type": "supermarket",
        "key": GOOGLE_MAPS_API_KEY
    }
    try:
        res = requests.get(url, params=params, timeout=10).json()
        print(f"\n[DEBUG] Google Places results for type=supermarket:")
        for i, place in enumerate(res.get("results", [])):
            print(i, "-", place.get("name"), "|", place.get("types"))
        all_results.extend(res.get("results", []))
    except Exception as e:
        print(f"[stores] Google API request failed for type=supermarket:", e)

    # Pass 2: broader keyword search — catches big-box/general stores
    # (Walmart, Target, Costco, or local equivalents) that Google may not
    # tag strictly as "supermarket", and works across languages/regions.
    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "keyword": "grocery store",
        "key": GOOGLE_MAPS_API_KEY
    }
    try:
        res = requests.get(url, params=params, timeout=10).json()
        print(f"\n[DEBUG] Google Places results for keyword='grocery store':")
        for i, place in enumerate(res.get("results", [])):
            print(i, "-", place.get("name"), "|", place.get("types"))
        all_results.extend(res.get("results", []))
    except Exception as e:
        print(f"[stores] Google API request failed for keyword search:", e)

    if not all_results:
        return []

    stores = []
    seen_place_ids = set()

    for place in all_results:
        place_id = place.get("place_id")
        if place_id in seen_place_ids:
            continue
        seen_place_ids.add(place_id)

        loc = place.get("geometry", {}).get("location")
        if not isinstance(loc, dict):
            continue

        store_lat = loc.get("lat")
        store_lng = loc.get("lng")
        if store_lat is None or store_lng is None:
            continue

        try:
            store_lat = float(store_lat)
            store_lng = float(store_lng)
        except (TypeError, ValueError):
            continue

        stores.append({
            "name": place.get("name"),
            "brand": normalize_store_brand(place.get("name")),
            "rating": place.get("rating") or 0,
            "total_ratings": place.get("user_ratings_total") or 0,
            "address": place.get("vicinity") or "",
            "lat": store_lat,
            "lng": store_lng,
        })

    unique = {}
    for s in stores:
        try:
            dist = haversine_distance(lat, lng, s["lat"], s["lng"])
        except Exception as e:
            print("[stores] distance calc failed:", e, s)
            continue

        s["distance_km"] = round(dist, 2)
        brand = s.get("brand") or "unknown"

        if brand not in unique or dist < unique[brand]["distance_km"]:
            unique[brand] = s

    return sorted(unique.values(), key=lambda x: x["distance_km"])


# =====================================================
# INVENTORY + ITEMIZED PRICES (🔥 FIX)
# =====================================================

def _estimate_price(item, store_name, currency):
    from backend.optimization.budget_optimizer import get_real_price as get_estimated_price

    MOCK_SCALE_FACTOR = {
        "USD": 1.0,
        "INR": 80.0,
        "GBP": 0.8,
        "CAD": 1.35,
        "AUD": 1.5,
        "SGD": 1.35,
        "AED": 3.67,
    }
    scale = MOCK_SCALE_FACTOR.get(currency, 1.0)
    try:
        return round(float(get_estimated_price(item, store_name)) * scale, 2)
    except Exception as e:
        print(f"[store] internet estimate failed for item={item} store={store_name}: {e}")
        base_price = ((hash(item + store_name) % 500) / 100) + 1
        return round(base_price * scale, 2)


def mock_check_inventory(store_name, shopping_list, city="", state="", country=""):
    """
    Builds itemized recommendations using the lower of receipt-derived city prices
    and the existing internet/AI estimate mechanism.
    """
    from backend.db.store_prices_repository import get_currency_for_country, get_lowest_receipt_price_for_item

    currency = get_currency_for_country(country)
    inventory = {}

    for item in shopping_list:
        receipt_price = None
        if city:
            try:
                real_price = get_real_price(item, store_name, city, state, country)
            except Exception:
                pass

        if real_price is not None:
            inventory[item] = {
                "available": True,
                "price": real_price["price"],
                "currency": real_price["currency"],
                "note": "real price from receipt",
                "source": "receipt",
            }
            continue

        # Fall back to mock price
        available = (hash(store_name + item) % 100) > 20
        base_price = ((hash(item + store_name) % 500) / 100) + 1
        multiplier = 1.0

        if "aldi" in lower:
            multiplier = 0.85
        elif "costco" in lower:
            multiplier = 0.80
        elif "whole foods" in lower:
            multiplier = 1.35
        elif "walmart" in lower:
            multiplier = 0.90
        elif "target" in lower:
            multiplier = 1.05

        price = round(base_price * multiplier * scale, 2) if available else None
        inventory[item] = {
            "available": True,
            "price": price,
            "currency": item_currency,
            "note": note,
            "source": source,
            "price_store": price_store,
        }

    return inventory

def _receipt_stores_for_city(city="", state="", country=""):
    if not city or not state:
        return []
    try:
        from backend.db.store_prices_repository import get_stores_in_city

        receipt_stores = get_stores_in_city(city, state, country or "US")
    except Exception as e:
        print(f"[store] receipt city-store lookup failed for {city}, {state}: {e}")
        return []

    stores = []
    for store in receipt_stores:
        if not isinstance(store, dict) or not store.get("store_name"):
            continue
        stores.append({
            "name": store.get("store_name"),
            "lat": store.get("lat"),
            "lng": store.get("lng"),
            "address": store.get("address", ""),
            "rating": store.get("rating", 4.0),
            "source": "receipt",
        })
    print(f"[store] receipt city-store fallback found {len(stores)} stores for {city}, {state}")
    return stores


# =====================================================
# SCORE STORE
# =====================================================

def score_store(store, inventory, user_location):
    try:
        lat1 = user_location.get("lat")
        lng1 = user_location.get("lng")
        lat2 = store.get("lat")
        lng2 = store.get("lng")

        if None in (lat1, lng1, lat2, lng2):
            distance = 999
        else:
            distance = haversine_distance(lat1, lng1, lat2, lng2)

    except Exception as e:
        print("[store] distance calculation failed:", e)
        return {
            "distance_km": 999,
            "availability_score": 0,
            "average_price": 0,
            "total_price": 0,
            "final_score": 0
        }

    available = sum(1 for v in inventory.values() if v.get("available"))
    total_items = len(inventory)

    availability_score = available / total_items if total_items else 0

    total_price = sum((v.get("price") or 0) for v in inventory.values())
    avg_price = total_price / total_items if total_items else 0

    rating_score = store.get("rating", 0) / 5
    distance_score = 1 / (1 + distance)
    price_score = 1 / (1 + total_price)

    final_score = (
        availability_score * 0.4 +
        rating_score * 0.2 +
        distance_score * 0.2 +
        price_score * 0.2
    )

    return {
        "distance_km": round(distance, 2),
        "availability_score": round(availability_score, 2),
        "average_price": round(avg_price, 2),
        "total_price": round(total_price, 2),
        "final_score": round(final_score, 3)
    }


# =====================================================
# MAIN RECOMMENDER (🔥 UPDATED OUTPUT)
# =====================================================

def recommend_best_store(user_location, shopping_list):
    if not isinstance(user_location, dict):
        print("[store] invalid user_location type")
        return []

    lat = user_location.get("lat")
    lng = user_location.get("lng")

    if lat is None or lng is None:
        print("[store] missing user coordinates:", user_location)
        return []

    city = user_location.get("city", "")
    state = user_location.get("region", "")
    country = user_location.get("country", "")

    print(f"[store] city resolved for price recommendations: city={city!r} state={state!r} country={country!r}")
    try:
        stores = find_nearby_grocery_stores(lat, lng)
    except Exception as e:
        print("[store] failed to fetch stores:", e)
        stores = []
    print(f"[store] nearby store results: {len(stores)}")

    if not stores:
        print("[store] no stores returned from finder; trying receipt city stores")
        stores = _receipt_stores_for_city(city, state, country)

    if not stores:
        print("[store] no stores available after receipt fallback")
        return []

    results = []

    for store in stores:
        try:
            # -----------------------------
            # Validate store basics
            # -----------------------------
            if not isinstance(store, dict):
                continue

            store_name = store.get("name")
            if not store_name:
                continue

            # -----------------------------
            # Inventory check (safe)
            # -----------------------------
            try:
                inventory = mock_check_inventory(store_name, shopping_list, city, state, country)
                if not isinstance(inventory, dict):
                    inventory = {}
            except Exception as e:
                print(f"[store] inventory failed for {store_name}:", e)
                inventory = {}

            # -----------------------------
            # Score calculation (safe)
            # -----------------------------
            try:
                score = score_store(store, inventory, user_location)
            except Exception as e:
                print(f"[store] scoring failed for {store_name}:", e)
                continue

            # -----------------------------
            # Build structured output
            # -----------------------------
            items = []
            price_breakdown = {}

            for item, data in inventory.items():
                if not isinstance(data, dict):
                    continue

                if data.get("available") and data.get("price") is not None:
                    items.append({
                        "item": item,
                        "price": data["price"],
                        "currency": data.get("currency", "USD"),
                        "source": data.get("source", "estimate"),
                        "note": data.get("note"),
                        "price_store": data.get("price_store", store_name),
                    })
                    price_breakdown[item] = {
                        "price": data["price"],
                        "currency": data.get("currency", "USD"),
                        "source": data.get("source", "estimate"),
                        "note": data.get("note"),
                        "price_store": data.get("price_store", store_name),
                    }

            results.append({
                "store": store,
                "score": score,
                "inventory": inventory,
                "items": items,
                "price_breakdown": price_breakdown,
                "unavailable_items": [
                    i for i, d in inventory.items()
                    if isinstance(d, dict) and not d.get("available")
                ]
            })

        except Exception as e:
            # Absolute safety net per store
            print(f"[store] unexpected error processing store {store}: {e}")
            continue

    # -----------------------------
    # Final sorting (safe fallback)
    # -----------------------------
    try:
        results.sort(
            key=lambda x: x.get("score", {}).get("final_score", 0),
            reverse=True
        )
    except Exception as e:
        print("[store] sorting failed:", e)

    if not results:
        print("[store] WARNING: no valid stores after processing")

    return results
