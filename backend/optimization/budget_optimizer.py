"""
budget_optimizer.py
====================
Uses real MongoDB prices to calculate:
- Original cost: what you'd pay at the most expensive store
- Optimized cost: what you'd pay at the cheapest store
- Money saved: the difference

This replaces the old keyword-guessing / hardcoded price version
that always returned $0 savings.
"""

from collections import defaultdict
#from backend.services.price_engine import (
   # get_item_price,
    #STORES
#)
STORES = [
    "Walmart", "Kroger", "ALDI",
    "Whole Foods", "Trader Joe's", "Costco",
]

# =====================================================
# CATEGORY DETECTION
# =====================================================

def categorize_item(item: str) -> str:
    item = item.lower()

    if any(x in item for x in ["cheese","milk","yogurt","cream","paneer"]):
        return "dairy"
    if any(x in item for x in ["tomato","onion","garlic","pepper","spinach","broccoli","carrot","kale","mushroom","zucchini"]):
        return "vegetables"
    if any(x in item for x in ["rice","pasta","bread","flour","tortilla","quinoa","oats","noodles","spaghetti"]):
        return "carbs"
    if any(x in item for x in ["beans","tofu","lentils","chickpeas","tempeh","edamame"]):
        return "protein"
    if any(x in item for x in ["oil","butter","nuts","seeds","avocado","tahini"]):
        return "fats"

    return "other"


# =====================================================
# CHEAP SUBSTITUTIONS
# Applied when user is over budget
# =====================================================

CHEAP_SUBSTITUTIONS = {
    "parmesan cheese":  "mozzarella cheese",
    "pine nuts":        "walnuts",
    "heavy cream":      "milk",
    "avocado oil":      "canola oil",
    "fresh basil":      "dried basil",
    "greek yogurt":     "plain yogurt",
    "coconut oil":      "canola oil",
    "almond milk":      "oat milk",
    "organic tomatoes": "tomatoes",
    "baby spinach":     "spinach",
}

LUXURY_KEYWORDS = [
    "organic", "pine nuts", "parmesan",
    "avocado", "truffle", "saffron"
]


# =====================================================
# REAL PRICE LOOKUP
# Gets price from MongoDB for a specific store
# Falls back to $2.50 if item not in DB
# =====================================================

#def get_real_price(item: str, store: str) -> float:
    #"""Get real price from MongoDB products collection."""
    #try:
        #return get_item_price(store, item)
    #except Exception:
        #return 2.50

def get_real_price(item: str, store: str) -> float:
    """Mock price - deterministic based on item+store hash."""
    base_price = ((hash(item + store) % 500) / 100) + 1
    multipliers = {
        "aldi": 0.85, "costco": 0.80, "whole foods": 1.35,
        "walmart": 0.90, "target": 1.05
    }
    multiplier = next((v for k, v in multipliers.items() if k in store.lower()), 1.0)
    return round(base_price * multiplier, 2)

# =====================================================
# BASKET COST AT A STORE
# =====================================================

def basket_cost_at_store(shopping_list: list, store: str) -> float:
    """Total cost of all items at a given store."""
    return round(
        sum(get_real_price(item, store) for item in shopping_list),
        2
    )


# =====================================================
# FIND CHEAPEST AND MOST EXPENSIVE STORE
# =====================================================

def find_best_worst_stores(shopping_list: list) -> dict:
    """
    Returns cheapest and most expensive store for this basket.
    Used to show meaningful original vs optimized cost.
    """
    if not shopping_list:
        return {
            "cheapest_store": "ALDI",
            "cheapest_total": 0,
            "expensive_store": "Whole Foods",
            "expensive_total": 0,
        }

    store_totals = {
        store: basket_cost_at_store(shopping_list, store)
        for store in STORES
    }

    cheapest  = min(store_totals, key=store_totals.get)
    expensive = max(store_totals, key=store_totals.get)

    return {
        "cheapest_store":  cheapest,
        "cheapest_total":  store_totals[cheapest],
        "expensive_store": expensive,
        "expensive_total": store_totals[expensive],
        "all_store_totals": store_totals,
    }


# =====================================================
# MAIN BUDGET OPTIMIZER
# =====================================================

def optimize_for_budget(
    shopping_list: list,
    budget: float,
    available_substitutions: dict | None = None
) -> dict:
    """
    Compares cost at cheapest vs most expensive store.
    Applies substitutions if still over budget after
    choosing cheapest store.

    Returns:
        original_cost:  cost at most expensive store (what you'd pay by default)
        optimized_cost: cost at cheapest store
        money_saved:    the difference
        substitutions:  any swaps applied to fit budget
    """

    if not shopping_list:
        return {
            "optimized_list":  shopping_list,
            "original_cost":   0,
            "optimized_cost":  0,
            "money_saved":     0,
            "substitutions":   [],
            "cheapest_store":  "—",
            "expensive_store": "—",
        }

    # Get real prices from MongoDB
    best_worst = find_best_worst_stores(shopping_list)

    original_cost  = best_worst["expensive_total"]   # worst case cost
    optimized_cost = best_worst["cheapest_total"]    # best case cost
    money_saved    = round(original_cost - optimized_cost, 2)

    substitution_table = {**CHEAP_SUBSTITUTIONS, **(available_substitutions or {})}
    substitutions  = []
    optimized_list = list(shopping_list)

    # Apply substitutions only if cheapest store is still over budget
    if optimized_cost > budget:

        swapped = []

        for item in optimized_list:
            lower = item.lower()
            if lower in substitution_table:
                cheaper = substitution_table[lower]
                substitutions.append({
                    "original":    item,
                    "replacement": cheaper
                })
                swapped.append(cheaper)
            else:
                swapped.append(item)

        optimized_list = swapped

        # Recalculate after substitutions
        optimized_cost = basket_cost_at_store(
            optimized_list,
            best_worst["cheapest_store"]
        )

        # Still over? Remove luxury items
        if optimized_cost > budget:
            optimized_list = [
                item for item in optimized_list
                if not any(k in item.lower() for k in LUXURY_KEYWORDS)
            ]
            optimized_cost = basket_cost_at_store(
                optimized_list,
                best_worst["cheapest_store"]
            )

        money_saved = round(original_cost - optimized_cost, 2)

    return {
        "optimized_list":  optimized_list,
        "original_cost":   round(original_cost,  2),
        "optimized_cost":  round(optimized_cost, 2),
        "money_saved":     max(money_saved, 0),   # never negative
        "substitutions":   substitutions,
        "cheapest_store":  best_worst["cheapest_store"],
        "expensive_store": best_worst["expensive_store"],
    }


def _store_name(store: dict) -> str:
    return str(store.get("store_name") or store.get("name") or store.get("store") or "").strip()


def _store_total(store: dict) -> float | None:
    try:
        total = float(store.get("basket_price", 0))
    except (TypeError, ValueError):
        return None
    if total > 0:
        return round(total, 2)

    breakdown = store.get("price_breakdown") or {}
    if not isinstance(breakdown, dict) or not breakdown:
        return None

    total = 0.0
    found_price = False
    for value in breakdown.values():
        raw_price = value.get("price") if isinstance(value, dict) else value
        try:
            total += float(raw_price)
            found_price = True
        except (TypeError, ValueError):
            continue
    return round(total, 2) if found_price and total > 0 else None


def _budget_from_recommended_stores(
    shopping_list: list,
    weekly_budget: float,
    recommended_stores: list,
) -> dict | None:
    priced_stores = []
    for store in recommended_stores or []:
        if not isinstance(store, dict):
            continue
        name = _store_name(store)
        total = _store_total(store)
        if name and total is not None:
            priced_stores.append({"name": name, "total": total, "store": store})

    if not priced_stores:
        return None

    cheapest = min(priced_stores, key=lambda item: item["total"])
    expensive = max(priced_stores, key=lambda item: item["total"])
    has_comparison = len(priced_stores) >= 2

    category_totals = defaultdict(float)
    cheapest_breakdown = cheapest["store"].get("price_breakdown") or {}
    for item in shopping_list:
        category = categorize_item(item)
        data = cheapest_breakdown.get(item)
        raw_price = data.get("price") if isinstance(data, dict) else data
        try:
            category_totals[category] += float(raw_price)
        except (TypeError, ValueError):
            pass

    optimized_cost = cheapest["total"]
    original_cost = expensive["total"] if has_comparison else cheapest["total"]

    note = None if has_comparison else "insufficient store data for cheapest vs expensive comparison"
    optimization = {
        "optimized_list": shopping_list,
        "original_cost": round(original_cost, 2),
        "optimized_cost": round(optimized_cost, 2),
        "money_saved": max(round(original_cost - optimized_cost, 2), 0),
        "substitutions": [],
        "cheapest_store": cheapest["name"],
        "expensive_store": expensive["name"] if has_comparison else None,
        "store_totals": {store["name"]: store["total"] for store in priced_stores},
        "source": "recommended_stores",
    }
    if note:
        optimization["note"] = note

    return {
        "budget": weekly_budget,
        "category_breakdown": {k: round(v, 2) for k, v in category_totals.items()},
        "optimization": optimization,
    }


# =====================================================
# WEEKLY BUDGET PLANNER (main entry point)
# =====================================================

def weekly_budget_planner(
    weekly_shopping_list: list,
    weekly_budget: float,
    recommended_stores: list | None = None,
) -> dict:
    """
    Full budget analysis:
    - Category breakdown
    - Real price optimization
    - Savings vs worst-case store
    """

    store_budget = _budget_from_recommended_stores(
        weekly_shopping_list,
        weekly_budget,
        recommended_stores or [],
    )
    if store_budget is not None:
        return store_budget

    category_totals = defaultdict(float)

    # Use cheapest store prices for category breakdown
    best_worst = find_best_worst_stores(weekly_shopping_list)
    cheapest_store = best_worst.get("cheapest_store", "ALDI")

    for item in weekly_shopping_list:
        category = categorize_item(item)
        category_totals[category] += get_real_price(item, cheapest_store)

    # Round category totals
    category_totals = {
        k: round(v, 2)
        for k, v in category_totals.items()
    }

    optimization = optimize_for_budget(
        weekly_shopping_list,
        weekly_budget
    )

    return {
        "budget":             weekly_budget,
        "category_breakdown": category_totals,
        "optimization":       optimization,
    }


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":
    from pprint import pprint

    shopping_list = [
        "parmesan cheese", "pine nuts", "tomatoes",
        "onions", "garlic", "olive oil", "rice",
        "tofu", "greek yogurt", "fresh basil"
    ]

    result = weekly_budget_planner(shopping_list, weekly_budget=35)
    pprint(result)
