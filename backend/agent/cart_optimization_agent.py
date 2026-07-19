import json
from typing import Any, Callable

from backend.core.gpt56_client import generate_primary_or_fallback
from backend.optimization.basket_optimizer import optimize_basket
from backend.optimization import budget_optimizer


def _normalize_items(items: list[Any]) -> list[str]:
    normalized = []
    seen = set()
    for item in items:
        if isinstance(item, str):
            value = item.strip().lower()
        elif isinstance(item, dict):
            value = str(item.get("name") or item.get("item") or "").strip().lower()
        else:
            continue
        if value and value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized


def _normalize_available_substitutions(substitutions: dict[str, Any] | None) -> dict[str, str]:
    normalized = {}
    for original, options in (substitutions or {}).items():
        original_key = str(original).strip().lower()
        if not original_key:
            continue
        if isinstance(options, list):
            replacement = next((str(option).strip().lower() for option in options if str(option).strip()), "")
        else:
            replacement = str(options).strip().lower()
        if replacement and replacement != "keep original":
            normalized[original_key] = replacement
    return normalized


def _remove_pantry_items(shopping_list: list[str], pantry_items: list[str]) -> tuple[list[str], list[str]]:
    pantry_lookup = set(_normalize_items(pantry_items))
    remaining = []
    removed = []

    for item in shopping_list:
        item_key = item.strip().lower()
        if item_key in pantry_lookup:
            removed.append(item)
        else:
            remaining.append(item)

    return remaining, removed


def _get_pantry_items(user_id: str) -> list[str]:
    from backend.db.pantry_repository import get_pantry

    return get_pantry(user_id)


def _build_store_inputs(shopping_list: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "name": store,
            "inventory": {
                item: {"price": budget_optimizer.get_real_price(item, store), "available": True, "currency": "USD"}
                for item in shopping_list
            },
        }
        for store in budget_optimizer.STORES
    ]


def _build_store_plan(shopping_list: list[str]) -> list[dict[str, Any]]:
    if not shopping_list:
        return []

    stores = _build_store_inputs(shopping_list)
    allocation = optimize_basket(stores, shopping_list)
    return [
        {
            "item": entry["item"],
            "store": entry["store"],
            "price": next(
                store["inventory"][entry["item"]]["price"]
                for store in stores
                if store["name"] == entry["store"]
            ),
            "currency": "USD",
        }
        for entry in allocation
    ]


def _format_steps(
    pantry_items: list[str],
    pantry_removed: list[str],
    clean_list: list[str],
    budget_result: dict[str, Any],
    store_plan: list[dict[str, Any]],
) -> list[dict[str, str]]:
    substitutions = budget_result.get("substitutions", []) or []
    compared_store_count = len({entry["store"] for entry in store_plan}) if store_plan else 0
    return [
        {
            "tool": "get_pantry",
            "status": "success",
            "summary": f"Checked pantry — found {len(pantry_items)} items and removed {len(pantry_removed)} from the cart",
        },
        {
            "tool": "optimize_for_budget",
            "status": "success",
            "summary": f"Applied {len(substitutions)} budget substitution(s) across {len(clean_list)} remaining items",
        },
        {
            "tool": "optimize_basket",
            "status": "success",
            "summary": f"Compared prices across {compared_store_count} store(s) for {len(store_plan)} item allocation(s)",
        },
    ]


def _default_summary_generator(prompt: str) -> str:
    def generate_with_gemini(summary_prompt: str) -> str:
        import os
        from vertexai.generative_models import GenerativeModel

        model = GenerativeModel(os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash"))
        return model.generate_content(summary_prompt).text

    text, _model_used = generate_primary_or_fallback(
        prompt,
        generate_with_gemini,
        log_prefix="optimize-cart-agent",
        primary=generate_with_gemini,
    )
    return text


def build_cart_optimization_plan(
    user_id: str,
    shopping_list: list[Any],
    substitutions: dict[str, Any] | None,
    budget: float,
    *,
    summary_generator: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    if not isinstance(shopping_list, list):
        raise ValueError("shopping_list must be a list")
    if substitutions is not None and not isinstance(substitutions, dict):
        raise ValueError("substitutions must be an object")

    clean_list = _normalize_items(shopping_list)
    if not clean_list:
        raise ValueError("shopping_list must contain at least one item")

    budget_value = float(budget)
    if budget_value < 0:
        raise ValueError("budget must be greater than or equal to 0")

    print(f"[optimize-cart-agent] starting for user={user_id}, items={len(clean_list)}, budget={budget_value}")
    pantry_items = _get_pantry_items(user_id)
    print(f"[optimize-cart-agent] pantry items found: {len(pantry_items)}")

    cart_after_pantry, pantry_removed = _remove_pantry_items(clean_list, pantry_items)
    print(f"[optimize-cart-agent] pantry items removed: {len(pantry_removed)}")

    available_substitutions = _normalize_available_substitutions(substitutions)
    budget_result = budget_optimizer.optimize_for_budget(
        cart_after_pantry,
        budget_value,
        available_substitutions=available_substitutions,
    )
    optimized_list = _normalize_items(budget_result.get("optimized_list", cart_after_pantry))
    substitutions_applied = budget_result.get("substitutions", []) or []
    print(f"[optimize-cart-agent] available substitutions considered: {len(available_substitutions)}")
    print(f"[optimize-cart-agent] substitutions applied: {len(substitutions_applied)}")

    store_plan = _build_store_plan(optimized_list)
    print(f"[optimize-cart-agent] store allocations built: {len(store_plan)}")

    original_total = round(float(budget_result.get("original_cost", 0)), 2)
    optimized_total = round(float(budget_result.get("optimized_cost", 0)), 2)
    estimated_savings = round(max(original_total - optimized_total, 0), 2)

    steps = _format_steps(pantry_items, pantry_removed, clean_list, budget_result, store_plan)

    prompt = f"""You are SmartCart's cart optimization narrator.
Summarize this deterministic optimization result in 3-4 concise bullets.
Do not invent prices, stores, or substitutions. Only use this JSON:
{json.dumps({
    "original_total": original_total,
    "optimized_total": optimized_total,
    "estimated_savings": estimated_savings,
    "pantry_removed": pantry_removed,
    "substitutions_applied": substitutions_applied,
    "store_plan": store_plan,
    "steps": steps,
}, indent=2)}"""
    summary = (summary_generator or _default_summary_generator)(prompt)
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("optimization summary was empty")

    return {
        "success": True,
        "summary": summary.strip(),
        "original_total": original_total,
        "optimized_total": optimized_total,
        "estimated_savings": estimated_savings,
        "pantry_removed": pantry_removed,
        "substitutions_applied": substitutions_applied,
        "store_plan": store_plan,
        "steps": steps,
    }
