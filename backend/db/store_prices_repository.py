import re
from datetime import datetime, timezone

from backend.db.firestore_client import db

COLLECTION = "store_prices"
CITY_COLLECTION = "city_prices"

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

COUNTRY_ALIASES = {
    "america": "US",
    "australia": "AU",
    "bharat": "IN",
    "canada": "CA",
    "great britain": "GB",
    "india": "IN",
    "singapore": "SG",
    "uae": "AE",
    "united arab emirates": "AE",
    "united kingdom": "GB",
    "united states": "US",
    "united states of america": "US",
    "usa": "US",
}


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def _make_id(value: str) -> str:
    normalized = _normalize_text(value)
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_") or "unknown"


def normalize_city(city: str) -> str:
    return _normalize_text(city)


def normalize_state(state: str) -> str:
    return _normalize_text(state)


def normalize_country(country: str) -> str:
    raw = (country or "US").strip()
    if not raw:
        return "US"
    upper = raw.upper()
    if upper in COUNTRY_CURRENCY_MAP:
        return upper
    return COUNTRY_ALIASES.get(_normalize_text(raw), upper)


def _city_key(city: str, state: str = "", country: str = "US") -> str:
    return _make_id("_".join([normalize_country(country), normalize_state(state), normalize_city(city)]))


def _item_key(item: str) -> str:
    return _make_id(item)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def _make_id(value: str) -> str:
    normalized = _normalize_text(value)
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_") or "unknown"


def normalize_city(city: str) -> str:
    return _normalize_text(city)


def normalize_state(state: str) -> str:
    return _normalize_text(state)


def normalize_country(country: str) -> str:
    return (country or "US").strip().upper() or "US"


def _city_key(city: str, state: str = "", country: str = "US") -> str:
    return _make_id("_".join([normalize_country(country), normalize_state(state), normalize_city(city)]))


def _item_key(item: str) -> str:
    return _make_id(item)


def get_currency_for_country(country: str) -> str:
    """Resolve an ISO country code/name to a currency code."""
    return COUNTRY_CURRENCY_MAP.get(normalize_country(country), "USD")


def _make_store_id(store_name: str, city: str, state: str) -> str:
    """
    Deterministic store ID so re-uploads for the same store merge into one
    document instead of creating duplicates. e.g. "Trader Joe's" + "Austin" +
    "TX" -> "traders_joes_austin_tx"
    """
    raw = f"{store_name}_{city}_{state}".lower().strip()
    raw = re.sub(r"[^a-z0-9]+", "_", raw)
    return raw.strip("_")




def _coerce_positive_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _extract_measurement(*values: object) -> str:
    text = " ".join(str(value or "") for value in values)
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*(g|gram|grams|kg|kilogram|kilograms|lb|lbs|pound|pounds|oz|ounce|ounces)\b", text, re.IGNORECASE)
    if not match:
        return ""
    unit = match.group(2).lower()
    unit = {"gram": "g", "grams": "g", "kilogram": "kg", "kilograms": "kg", "lbs": "lb", "pound": "lb", "pounds": "lb", "ounce": "oz", "ounces": "oz"}.get(unit, unit)
    return f"{match.group(1)} {unit}"


def _receipt_quantity(data: dict) -> float:
    for key in ("quantity", "qty", "count", "item_count", "no_of_items", "number_of_items"):
        qty = _coerce_positive_float(data.get(key))
        if qty is not None:
            return qty
    return 1.0


def _receipt_line_price(data: dict):
    for key in ("line_total", "line_price", "total_price", "total", "amount", "price"):
        price = _coerce_positive_float(data.get(key))
        if price is not None:
            return price
    return None

def _clean_items(items: dict, currency: str, uploaded_by: str, receipt_date: str, now: str) -> dict:
    cleaned = {}
    for raw_name, raw_data in (items or {}).items():
        name = _normalize_text(raw_name)
        if not name:
            continue
        data = raw_data if isinstance(raw_data, dict) else {"price": raw_data}
        quantity = _receipt_quantity(data)
        line_price = _receipt_line_price(data)
        if line_price is None:
            continue
        list_price = round(line_price / quantity, 2)
        measurement = _extract_measurement(name, data.get("measurement"), data.get("unit"))
        cleaned[name] = {
            "price": list_price,
            "line_price": round(line_price, 2),
            "quantity": quantity,
            "unit": data.get("unit", ""),
            "measurement": measurement,
            "currency": data.get("currency", currency),
            "last_updated": now,
            "uploaded_by": uploaded_by,
            "receipt_date": receipt_date,
        }
    return cleaned


def _city_doc(city: str, state: str = "", country: str = "US"):
    return db.collection(CITY_COLLECTION).document(_city_key(city, state, country))


def _item_result_from_prices(item_doc: dict, store_id: str, store_name: str = ""):
    prices = item_doc.get("prices", {}) if item_doc else {}
    if not prices:
        return None

    selected = None
    if store_id and store_id in prices:
        selected = prices[store_id]
    elif store_name:
        normalized_store = _normalize_text(store_name)
        selected = next(
            (price for price in prices.values() if _normalize_text(price.get("store_name", "")) == normalized_store),
            None,
        )
    if selected is None:
        selected = min(prices.values(), key=lambda price: float(price.get("price", float("inf"))))

    price = selected.get("price")
    if price is None:
        return None
    return {
        "price": float(price),
        "currency": selected.get("currency") or item_doc.get("currency", "USD"),
        "measurement": selected.get("measurement", ""),
        "quantity": selected.get("quantity", 1),
    }


def get_real_price(item: str, store_name: str, city: str, state: str, country: str = "US"):
    """
    Looks up a real, receipt-derived price for a specific item in the shared
    city_prices dataset. If the requested store has no uploaded price, returns
    the lowest city-level receipt price for that item. Falls back to legacy
    store_prices docs only if the city-keyed item is missing.
    """
    city_key = _city_key(city, state, country)
    item_key = _item_key(item)
    store_id = _make_store_id(store_name, normalize_city(city), normalize_state(state))
    print(f"[store_prices] read city_prices/{city_key}/items/{item_key} store={store_id}")

    city_item = db.collection(CITY_COLLECTION).document(city_key).collection("items").document(item_key).get()
    if city_item.exists:
        result = _item_result_from_prices(city_item.to_dict(), store_id, store_name)
        if result:
            print(f"[store_prices] city price hit for item={item_key}: {result}")
            return result

    city_items = db.collection(CITY_COLLECTION).document(city_key).collection("items").stream()
    normalized_item = normalize_city(item)
    for doc in city_items:
        item_doc = doc.to_dict()
        known_item = item_doc.get("name", "")
        if known_item in normalized_item or normalized_item in known_item:
            result = _item_result_from_prices(item_doc, store_id, store_name)
            if result:
                print(f"[store_prices] fuzzy city price hit for item={item_key}: {result}")
                return result

    legacy_store_id = _make_store_id(store_name, city, state)
    legacy_doc = db.collection(COLLECTION).document(legacy_store_id).get()
    if not legacy_doc.exists:
        print(f"[store_prices] price miss for city={city_key}, item={item_key}")
        return None

    doc_data = legacy_doc.to_dict()
    items = doc_data.get("items", {})
    store_currency = doc_data.get("currency") or get_currency_for_country(doc_data.get("country"))

    def _legacy_result(data):
        price = data.get("price")
        if price is None:
            return None
        return {"price": float(price), "currency": data.get("currency", store_currency)}

    if normalized_item in items:
        return _legacy_result(items[normalized_item])

    for known_item, data in items.items():
        if known_item in normalized_item or normalized_item in known_item:
            return _legacy_result(data)

    return None


def _iter_legacy_store_price_docs(city: str, state: str = "", country: str = "US"):
    normalized_city = normalize_city(city)
    normalized_state = normalize_state(state)
    normalized_country = normalize_country(country)
    print(f"[store_prices] query store_prices where city == {normalized_city}")

    collection = db.collection(COLLECTION)
    try:
        docs = collection.where("city", "==", normalized_city).stream()
    except Exception as e:
        print(f"[store_prices] city where query unavailable, streaming store_prices instead: {e}")
        docs = collection.stream()

    for doc in docs:
        data = doc.to_dict() or {}
        if normalize_city(data.get("city", "")) != normalized_city:
            continue
        if normalized_state and normalize_state(data.get("state", "")) != normalized_state:
            continue
        doc_country = normalize_country(data.get("country") or country)
        if country and doc_country != normalized_country:
            continue
        yield doc.id, data


def _receipt_currency(item_data: dict, store_data: dict, requested_country: str) -> str:
    doc_country = store_data.get("country") or requested_country
    country_currency = get_currency_for_country(doc_country)
    if normalize_country(doc_country) != "US":
        return country_currency
    return item_data.get("currency") or store_data.get("currency") or country_currency


def get_lowest_receipt_price_for_item(item: str, city: str, state: str = "", country: str = "US"):
    """Return the lowest matching receipt price from legacy store_prices docs for a city."""
    normalized_item = _normalize_text(item)
    if not normalized_item or not city:
        return None

    best = None
    for store_id, store_data in _iter_legacy_store_price_docs(city, state, country):
        items = store_data.get("items") or {}
        for known_item, raw_data in items.items():
            known_normalized = _normalize_text(known_item)
            if not known_normalized:
                continue
            if known_normalized != normalized_item and known_normalized not in normalized_item and normalized_item not in known_normalized:
                continue
            item_data = raw_data if isinstance(raw_data, dict) else {"price": raw_data}
            try:
                price = float(item_data.get("price"))
            except (TypeError, ValueError):
                continue
            candidate = {
                "price": price,
                "currency": _receipt_currency(item_data, store_data, country),
                "store_id": store_id,
                "store_name": store_data.get("store_name") or store_id,
                "source": "receipt",
                "item_name": known_normalized,
                "measurement": item_data.get("measurement", ""),
                "quantity": item_data.get("quantity", 1),
            }
            if best is None or candidate["price"] < best["price"]:
                best = candidate

    print(f"[store_prices] receipt lookup result item={normalized_item} city={normalize_city(city)}: {best}")
    return best


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
    Saves receipt-derived item prices to shared city_prices Firestore docs.
    Legacy store_prices docs are still updated for backward compatibility.

    Primary structure:
      city_prices/{normalized_country_state_city}
      city_prices/{normalized_country_state_city}/stores/{store_id}
      city_prices/{normalized_country_state_city}/items/{item_name}
    """
    now = datetime.now(timezone.utc).isoformat()
    country = normalize_country(country)
    normalized_city = normalize_city(city)
    normalized_state = normalize_state(state)
    currency = get_currency_for_country(country)
    cleaned_items = _clean_items(items or {}, currency, uploaded_by, receipt_date, now)

    if not cleaned_items:
        raise ValueError("No valid receipt items to save.")
    if not normalized_city or not normalized_state:
        raise ValueError("City and state are required to save receipt prices.")

    city_key = _city_key(normalized_city, normalized_state, country)
    store_id = _make_store_id(store_name, normalized_city, normalized_state)
    city_ref = db.collection(CITY_COLLECTION).document(city_key)
    store_ref = city_ref.collection("stores").document(store_id)
    print(f"[store_prices] writing city_prices/{city_key} store={store_id} items={len(cleaned_items)}")

    city_ref.set({
        "city": normalized_city,
        "state": normalized_state,
        "country": country,
        "display_city": city.strip(),
        "display_state": state.strip(),
        "last_updated": now,
    }, merge=True)

    store_ref.set({
        "store_id": store_id,
        "store_name": store_name,
        "city": normalized_city,
        "state": normalized_state,
        "country": country,
        "currency": currency,
        "address": address,
        "lat": lat,
        "lng": lng,
        "item_count": len(cleaned_items),
        "last_updated": now,
    }, merge=True)

    for item_name, item_data in cleaned_items.items():
        item_ref = city_ref.collection("items").document(_item_key(item_name))
        existing = item_ref.get()
        existing_data = existing.to_dict() if existing.exists else {}
        prices = existing_data.get("prices", {})
        prices[store_id] = {
            "store_id": store_id,
            "store_name": store_name,
            **item_data,
        }
        lowest = min(prices.values(), key=lambda price: float(price.get("price", float("inf"))))
        item_ref.set({
            "name": item_name,
            "city": normalized_city,
            "state": normalized_state,
            "country": country,
            "currency": lowest.get("currency", currency),
            "lowest_price": float(lowest["price"]),
            "lowest_store_id": lowest.get("store_id"),
            "lowest_store_name": lowest.get("store_name"),
            "prices": prices,
            "last_updated": now,
        }, merge=True)

    legacy_store_id = _make_store_id(store_name, normalized_city, normalized_state)
    legacy_ref = db.collection(COLLECTION).document(legacy_store_id)
    existing = legacy_ref.get()
    existing_data = existing.to_dict() if existing.exists else {}
    existing_items = existing_data.get("items", {})
    legacy_ref.set({
        "store_name": store_name,
        "city": normalized_city,
        "state": normalized_state,
        "country": country,
        "currency": currency,
        "address": address,
        "lat": lat,
        "lng": lng,
        "items": {**existing_items, **cleaned_items},
        "last_updated": now,
    }, merge=True)

    result = {
        "success": True,
        "item_count": len(cleaned_items),
        "store_id": store_id,
        "city_key": city_key,
        "city": normalized_city,
        "state": normalized_state,
        "items_preview": dict(list(cleaned_items.items())[:5]),
        "sample_path": f"{CITY_COLLECTION}/{city_key}/items/{_item_key(next(iter(cleaned_items)))}",
    }
    print(f"[store_prices] write result: {result}")
    return result


def get_stores_in_city(city: str, state: str, country: str = "US") -> list:
    city_key = _city_key(city, state, country)
    print(f"[store_prices] listing city_prices/{city_key}/stores")
    stores = []
    for doc in db.collection(CITY_COLLECTION).document(city_key).collection("stores").stream():
        stores.append(doc.to_dict())
    print(f"[store_prices] found {len(stores)} stores for city={city_key}")
    return stores
