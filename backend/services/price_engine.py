"""
price_engine.py
================
Deterministic price estimates used by grocery optimization flows.

This module uses local estimates so planning and optimization flows work
without an external product-price database dependency.
"""

import re


STORE_MODIFIERS = {
    "walmart": 0.95,
    "kroger": 1.00,
    "aldi": 0.82,
    "whole foods": 1.35,
    "trader joe": 1.05,
    "costco": 0.88,
}

DEFAULT_PRICE = 2.50

STORES = [
    "Walmart",
    "Kroger",
    "ALDI",
    "Whole Foods",
    "Trader Joe's",
    "Costco",
]


def normalize_item_name(item: str) -> str:
    """Clean item text before estimating prices."""
    item = str(item or "").lower().strip()
    prefixes = [
        "organic", "fresh", "frozen", "canned", "dried",
        "sliced", "diced", "chopped", "whole", "raw",
        "roasted", "unsalted", "salted", "low-fat", "fat-free",
    ]
    for prefix in prefixes:
        item = re.sub(rf"^{prefix}\s+", "", item)
    return item.strip()


def _item_base_price(item: str) -> float:
    clean_item = normalize_item_name(item)
    if not clean_item:
        return DEFAULT_PRICE
    return DEFAULT_PRICE + ((sum(ord(ch) for ch in clean_item) % 275) / 100)


def _store_modifier(store_name: str) -> float:
    store_lower = str(store_name or "").lower()
    return next((mod for key, mod in STORE_MODIFIERS.items() if key in store_lower), 1.0)


def get_item_price(store_name: str, item: str) -> float:
    """Return a deterministic estimated price for one item at one store."""
    return round(_item_base_price(item) * _store_modifier(store_name), 2)


def get_basket_price(store_name: str, shopping_list: list) -> dict:
    """Return total basket cost and per-item breakdown for a store."""
    breakdown = {}
    total = 0.0
    for item in shopping_list:
        price = get_item_price(store_name, item)
        breakdown[item] = price
        total += price
    return {"store": store_name, "breakdown": breakdown, "total": round(total, 2)}


def compare_prices(shopping_list: list) -> list:
    """Return basket estimates at all stores, sorted cheapest first."""
    results = [get_basket_price(store, shopping_list) for store in STORES]
    results.sort(key=lambda x: x["total"])
    return results


def cheapest_store_for_item(item: str) -> dict:
    """Return the cheapest estimated store for one item."""
    prices = {store: get_item_price(store, item) for store in STORES}
    cheapest = min(prices, key=prices.get)
    return {
        "item": normalize_item_name(item) or str(item or ""),
        "cheapest_store": cheapest,
        "price": prices[cheapest],
        "all_prices": prices,
    }


if __name__ == "__main__":
    test_list = ["olive oil", "tomatoes", "garlic", "pasta", "tofu", "spinach", "lentils"]
    print("=== Price Comparison ===")
    for result in compare_prices(test_list):
        print(f"  {result['store']:<15} ${result['total']:.2f}")
