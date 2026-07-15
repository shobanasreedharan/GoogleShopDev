"""Deterministic tool wrappers for the SmartCart chat agent.

These wrappers normalize backend capabilities into a common trace-friendly
shape without calling Gemini or formatting final chat responses. Day 2 can use
these results to build an agent action trace while keeping tool execution
separate from LLM summarization.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

ToolStatus = Literal["success", "error"]


class ToolResult(TypedDict):
    name: str
    status: ToolStatus
    summary: str
    data: Any


def _success(name: str, summary: str, data: Any) -> ToolResult:
    return {"name": name, "status": "success", "summary": summary, "data": data}


def _error(name: str, error: Exception | str) -> ToolResult:
    message = str(error) or "Unknown tool error"
    return {"name": name, "status": "error", "summary": message, "data": None}


def get_pantry_items(user_id: str) -> ToolResult:
    """Read the authenticated user's pantry from Firestore.

    Mirrors the deployed MCP tool name `get_pantry_items` while calling the
    repository directly so the wrapper remains deterministic and LLM-free.
    """
    name = "get_pantry_items"
    try:
        if not user_id:
            raise ValueError("user_id is required")

        from backend.db.pantry_repository import get_pantry

        items = get_pantry(user_id) or []
        data = {"user_id": user_id, "items": items, "count": len(items)}
        return _success(name, f"Found {len(items)} pantry item(s).", data)
    except Exception as exc:  # keep wrappers safe for trace capture
        return _error(name, exc)


def list_recipes(user_id: str) -> ToolResult:
    """List saved recipe cache entries for a user."""
    name = "list_recipes"
    try:
        if not user_id:
            raise ValueError("user_id is required")

        from backend.db.recipe_cache_repository import list_recipes as _list_recipes

        recipes = _list_recipes(user_id) or []
        data = {"user_id": user_id, "recipes": recipes, "count": len(recipes)}
        return _success(name, f"Found {len(recipes)} saved recipe(s).", data)
    except Exception as exc:
        return _error(name, exc)


def compare_stores(user_location: dict[str, Any], shopping_list: list[str], limit: int = 3) -> ToolResult:
    """Compare nearby stores for a shopping list using existing price/store logic.

    `user_location` should contain at least `lat` and `lng`; `city`, `region`,
    and `country` are used by the store finder to prefer receipt-derived prices
    when available.
    """
    name = "compare_stores"
    try:
        if not isinstance(user_location, dict):
            raise ValueError("user_location must be a dict")
        if user_location.get("lat") is None or user_location.get("lng") is None:
            raise ValueError("user_location.lat and user_location.lng are required")

        clean_items = [str(item).strip().lower() for item in (shopping_list or []) if str(item).strip()]
        if not clean_items:
            raise ValueError("shopping_list must contain at least one item")

        from backend.services.store_finder import recommend_best_store
        from backend.utils.sanitizers import clean_stores

        raw_results = recommend_best_store(user_location, clean_items) or []
        stores = clean_stores(raw_results)[: max(limit, 0)]

        formatted = []
        for result in stores:
            store = result.get("store", {}) or {}
            score = result.get("score", {}) or {}
            formatted.append({
                "store_name": store.get("name"),
                "brand": store.get("brand"),
                "address": store.get("address"),
                "lat": store.get("lat"),
                "lng": store.get("lng"),
                "basket_price": score.get("total_price", 0),
                "distance_km": score.get("distance_km", 0),
                "final_score": score.get("final_score", 0),
                "items": result.get("items", []),
                "price_breakdown": result.get("price_breakdown", {}),
                "unavailable_items": result.get("unavailable_items", []),
            })

        data = {
            "user_location": user_location,
            "shopping_list": clean_items,
            "stores": formatted,
            "count": len(formatted),
        }
        return _success(name, f"Compared {len(formatted)} store(s) for {len(clean_items)} item(s).", data)
    except Exception as exc:
        return _error(name, exc)
