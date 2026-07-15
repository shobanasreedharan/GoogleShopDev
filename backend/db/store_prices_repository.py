import re
from datetime import datetime, timezone

from backend.db.firestore_client import db

COLLECTION = "store_prices"

# Minimal country -> currency map. Extend as you add more markets.
COUNTRY_CURRENCY_MAP = {
    "US": "USD",
    "IN": "INR",
    "GB": "GBP",
    "CA": "CAD",
    "AU": "AUD",
    "SG": "SGD",
    "AE": "AED",
}


def get_currency_for_country(country: str) -> str:
    """Resolve an ISO country code to a currency code. Defaults to USD only
    if the country is unknown/blank — every real caller should be passing
    a resolved country from location.py, not relying on this default."""
    if not country:
        return "USD"
    return COUNTRY_CURRENCY_MAP.get(country.upper().strip(), "USD")


def _make_store_id(store_name: str, city: str, state: str) -> str:
    """
    Deterministic store ID so re-uploads for the same store merge into one
    document instead of creating duplicates. e.g. "Trader Joe's" + "Austin" +
    "TX" -> "traders_joes_austin_tx"
    """
    raw = f"{store_name}_{city}_{state}".lower().strip()
    raw = re.sub(r"[^a-z0-9]+", "_", raw)
    return raw.strip("_")


def get_real_price(item: str, store_name: str, city: str, state: str):
    """
    Looks up a real, receipt-derived price for a specific item at a specific
    store. Returns {"price": float, "currency": str} if found, or None if no
    real data exists yet for this item/store combination.

    Used by store_finder.py as the first choice before falling back to
    estimated/mock prices. Callers must read the "currency" field rather
    than assuming USD.
    """
    store_id = _make_store_id(store_name, city, state)
    doc = db.collection(COLLECTION).document(store_id).get()

    if not doc.exists:
        return None

    doc_data = doc.to_dict()
    items = doc_data.get("items", {})
    # Fall back through: per-item currency -> store-level currency -> USD
    store_currency = doc_data.get("currency") or get_currency_for_country(doc_data.get("country"))
    item_key = item.lower().strip()

    def _result(data):
        price = data.get("price")
        if price is None:
            return None
        return {
            "price": float(price),
            "currency": data.get("currency", store_currency),
        }

    # Exact match first
    if item_key in items:
        result = _result(items[item_key])
        if result:
            return result

    # Fuzzy: item contains a known item name, or vice versa
    for known_item, data in items.items():
        if known_item in item_key or item_key in known_item:
            result = _result(data)
            if result:
                return result

    return None


def save_store_prices(
    uploaded_by: str,
    store_name: str,
    city: str,
    state: str,
    country: str = "US",
    address: str = "",
    items: dict = None,
    receipt_date: str = "",
    lat: float = None,
    lng: float = None,
) -> dict:
    """
    Saves receipt-derived item prices to a shared store_prices Firestore
    collection, keyed by a deterministic store_id. Multiple receipts for
    the same store merge into one document, so item prices stay current
    as new receipts come in.

    Returns {"success": True, "item_count": int, "store_id": str}
    """
    items = items or {}
    if not items:
        return {"success": False, "error": "No items to save.", "item_count": 0, "store_id": None}

    store_id = _make_store_id(store_name, city, state)
    doc_ref = db.collection(COLLECTION).document(store_id)

    now = datetime.now(timezone.utc).isoformat()
    currency = get_currency_for_country(country)

    existing = doc_ref.get()
    existing_data = existing.to_dict() if existing.exists else {}
    existing_items = existing_data.get("items", {})

    # Merge new items over existing ones — newer receipt data wins per item
    merged_items = {**existing_items}
    for item_name, item_data in items.items():
        merged_items[item_name] = {
            **item_data,
            "currency": item_data.get("currency", currency),
            "last_updated": now,
            "uploaded_by": uploaded_by,
            "receipt_date": receipt_date,
        }

    doc_ref.set({
        "store_name": store_name,
        "city": city,
        "state": state,
        "country": country,
        "currency": currency,
        "address": address,
        "lat": lat,
        "lng": lng,
        "items": merged_items,
        "last_updated": now,
    }, merge=True)

    return {
        "success": True,
        "item_count": len(items),          # items added/updated in this upload
        "total_items": len(merged_items),  # total items now known for this store
        "store_id": store_id,
    }
