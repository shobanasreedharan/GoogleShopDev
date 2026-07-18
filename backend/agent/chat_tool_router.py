"""Deterministic tool routing for SmartCart chat.

This module decides which Day 1 wrappers to run before the LLM sees the
message. It intentionally contains no Gemini calls so it can be tested in
isolation and reused by the FastAPI route.
"""

from __future__ import annotations

import json
import re
from typing import Any

from backend.agent import tool_wrappers

PANTRY_KEYWORDS = ("pantry", "cook", "meal", "ingredients")
RECIPE_KEYWORDS = ("saved recipes", "my recipes")
STORE_KEYWORDS = ("store", "price", "budget", "where to buy")

DEFAULT_CHAT_LOCATION = {
    "lat": 32.7767,
    "lng": -96.7970,
    "city": "Dallas",
    "region": "TX",
    "country": "US",
}

_STOPWORDS = {
    "where", "to", "buy", "store", "stores", "price", "prices", "budget",
    "cheap", "cheapest", "find", "get", "for", "the", "a", "an", "my",
    "near", "nearby", "best", "should", "i", "can", "you", "please",
}


def _mentions(message: str, keywords: tuple[str, ...]) -> bool:
    normalized = message.lower()
    return any(keyword in normalized for keyword in keywords)


def extract_shopping_items(message: str) -> list[str]:
    """Best-effort deterministic item extraction for store comparison chat.

    The chat schema does not yet accept a shopping list or location. Until Day 3
    adds richer frontend context, this extracts lightweight item terms from the
    user message so `compare_stores` can still call the real store/price layer.
    """
    lowered = message.lower()
    for phrase in ("where to buy", "price of", "prices for", "buy"):
        lowered = lowered.replace(phrase, " ")
    tokens = re.findall(r"[a-z][a-z\-']*", lowered)
    items = [token.strip("-'") for token in tokens if token not in _STOPWORDS]
    return list(dict.fromkeys(item for item in items if item))[:8]


def route_chat_tools(
    message: str,
    user_id: str,
    user_location: dict[str, Any] | None = None,
) -> list[tool_wrappers.ToolResult]:
    """Run deterministic wrappers whose keyword categories match `message`."""
    results: list[tool_wrappers.ToolResult] = []

    if _mentions(message, PANTRY_KEYWORDS):
        results.append(tool_wrappers.get_pantry_items(user_id))

    if _mentions(message, RECIPE_KEYWORDS):
        results.append(tool_wrappers.list_recipes(user_id))

    if _mentions(message, STORE_KEYWORDS):
        shopping_items = extract_shopping_items(message)
        if not shopping_items:
            shopping_items = [message.strip().lower()] if message.strip() else []
        results.append(tool_wrappers.compare_stores(
            user_location or DEFAULT_CHAT_LOCATION,
            shopping_items,
        ))

    return results


def build_steps(tool_results: list[tool_wrappers.ToolResult]) -> list[dict[str, str]]:
    return [
        {
            "tool": result["name"],
            "status": result["status"],
            "summary": result["summary"],
        }
        for result in tool_results
    ]


def build_cards(tool_results: list[tool_wrappers.ToolResult]) -> dict[str, list[Any]]:
    cards: dict[str, list[Any]] = {"shopping_list": [], "stores": [], "recipes": []}
    for result in tool_results:
        if result["status"] != "success" or not isinstance(result.get("data"), dict):
            continue
        data = result["data"]
        if result["name"] == "get_pantry_items":
            cards["shopping_list"] = data.get("items", []) or []
        elif result["name"] == "list_recipes":
            cards["recipes"] = data.get("recipes", []) or []
        elif result["name"] == "compare_stores":
            cards["stores"] = data.get("stores", []) or []
    return cards


def build_tool_context(tool_results: list[tool_wrappers.ToolResult]) -> str:
    if not tool_results:
        return "No backend tools matched this message."
    return json.dumps(tool_results, indent=2, default=str)


def build_chat_response_payload(
    response_text: str,
    session_id: str,
    tool_results: list[tool_wrappers.ToolResult],
    usage: dict[str, Any],
) -> dict[str, Any]:
    """Build the structured `/chat` response envelope expected by Day 2."""
    return {
        "response": response_text,
        "session_id": session_id,
        "steps": build_steps(tool_results),
        "cards": build_cards(tool_results),
        "usage": usage,
    }
