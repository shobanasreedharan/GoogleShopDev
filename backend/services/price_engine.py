"""
price_engine.py
================
Queries MongoDB products collection for real prices.
Replaces the old hardcoded 6-item / $2-default version.
"""

from pymongo import MongoClient
from dotenv import load_dotenv
import os
import re

load_dotenv()

MONGODB_URI = os.getenv("MONGO_URI")          # matches mongo_client.py
DB_NAME     = os.getenv("MONGO_DB", "smart_grocery")  # matches mongo_client.py


# =====================================================
# DB CONNECTION (lazy singleton)
# =====================================================

_client = None
_db     = None

def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(MONGODB_URI)
        _db     = _client[DB_NAME]
    return _db


# =====================================================
# STORE PRICE MODIFIERS
# Used as fallback when item isn't in MongoDB
# =====================================================

STORE_MODIFIERS = {
    "walmart":     0.95,
    "kroger":      1.00,
    "aldi":        0.82,
    "whole foods": 1.35,
    "trader joe":  1.05,
    "costco":      0.88,
}

DEFAULT_PRICE = 2.50   # fallback for completely unknown items


# =====================================================
# NORMALIZE: fuzzy-match item name to DB product
# =====================================================

def normalize_item_name(item: str) -> str:
    """
    Clean and normalize item name for MongoDB lookup.
    e.g. "Fresh Basil Leaves" → "fresh basil"
         "Organic Tomatoes"   → "tomatoes"
    """
    item = item.lower().strip()

    # Strip common adjective prefixes
    prefixes = [
        "organic", "fresh", "frozen", "canned", "dried",
        "sliced", "diced", "chopped", "whole", "raw",
        "roasted", "unsalted", "salted", "low-fat", "fat-free"
    ]
    for prefix in prefixes:
        item = re.sub(rf"^{prefix}\s+", "", item)

    return item.strip()


# =====================================================
# CORE: GET PRICE FOR ONE ITEM AT ONE STORE
# =====================================================

def get_item_price(store_name: str, item: str) -> float:
    """
    Returns price of item at given store.
    Priority:
      1. Exact match in MongoDB products collection
      2. Fuzzy partial match in MongoDB
      3. Fallback: estimated price using store modifier
    """

    db           = get_db()
    col          = db["products"]
    clean_item   = normalize_item_name(item)
    store_key    = store_name.strip()

    # ── 1. Exact name match ───────────────────────
    doc = col.find_one({"name": clean_item})

    if doc:
        price = doc.get("prices", {}).get(store_key)
        if price is not None:
            return round(float(price), 2)

    # ── 2. Partial / contains match ───────────────
    doc = col.find_one({
        "name": {"$regex": clean_item, "$options": "i"}
    })

    if doc:
        price = doc.get("prices", {}).get(store_key)
        if price is not None:
            return round(float(price), 2)

    # ── 3. Reverse partial: item contains DB name ─
    #    e.g. item="cherry tomatoes" matches DB "tomatoes"
    all_products = col.find({}, {"name": 1, "prices": 1})
    for product in all_products:
        if product["name"] in clean_item:
            price = product.get("prices", {}).get(store_key)
            if price is not None:
                return round(float(price), 2)

    # ── 4. Fallback: store modifier on default price
    modifier = 1.0
    store_lower = store_name.lower()
    for key, mod in STORE_MODIFIERS.items():
        if key in store_lower:
            modifier = mod
            break

    estimated = round(DEFAULT_PRICE * modifier, 2)
    print(
        f"[price_engine] No DB price for '{item}' at '{store_name}'. "
        f"Using estimate: ${estimated}"
    )
    return estimated


# =====================================================
# BASKET TOTAL FOR A STORE
# =====================================================

def get_basket_price(store_name: str, shopping_list: list) -> dict:
    """
    Returns total basket cost and per-item breakdown for a store.
    """

    breakdown = {}
    total     = 0.0

    for item in shopping_list:
        price          = get_item_price(store_name, item)
        breakdown[item] = price
        total          += price

    return {
        "store":     store_name,
        "breakdown": breakdown,
        "total":     round(total, 2),
    }


# =====================================================
# PRICE COMPARISON ACROSS ALL STORES
# =====================================================

STORES = [
    "Walmart",
    "Kroger",
    "ALDI",
    "Whole Foods",
    "Trader Joe's",
    "Costco",
]

def compare_prices(shopping_list: list) -> list:
    """
    Returns basket cost at all 6 stores, sorted cheapest first.
    Used by budget_optimizer to recommend the best store.
    """

    results = []

    for store in STORES:
        basket = get_basket_price(store, shopping_list)
        results.append(basket)

    results.sort(key=lambda x: x["total"])

    return results


# =====================================================
# CHEAPEST STORE FOR A SINGLE ITEM
# =====================================================

def cheapest_store_for_item(item: str) -> dict:
    """
    Returns which store sells this item cheapest.
    Used by substitution agent for budget recommendations.
    """

    db         = get_db()
    col        = db["products"]
    clean_item = normalize_item_name(item)

    doc = col.find_one(
        {"name": {"$regex": clean_item, "$options": "i"}},
        {"prices": 1, "name": 1}
    )

    if not doc:
        return {"item": item, "cheapest_store": "ALDI", "price": DEFAULT_PRICE}

    prices = {
        store: price
        for store, price in doc.get("prices", {}).items()
        if price is not None
    }

    if not prices:
        return {"item": item, "cheapest_store": "ALDI", "price": DEFAULT_PRICE}

    cheapest = min(prices, key=prices.get)

    return {
        "item":           doc["name"],
        "cheapest_store": cheapest,
        "price":          prices[cheapest],
        "all_prices":     prices,
    }


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":
    import json

    test_list = [
        "olive oil", "tomatoes", "garlic",
        "pasta", "tofu", "spinach", "lentils"
    ]

    print("=== Price Comparison ===")
    results = compare_prices(test_list)
    for r in results:
        print(f"  {r['store']:<15} ${r['total']:.2f}")

    print("\n=== Cheapest Store per Item ===")
    for item in test_list[:3]:
        result = cheapest_store_for_item(item)
        print(
            f"  {item:<15} → "
            f"{result['cheapest_store']} "
            f"(${result['price']:.2f})"
        )