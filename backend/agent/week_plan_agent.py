import json
from typing import Any

from backend.agent.cart_optimization_agent import _normalize_items, _remove_pantry_items
from backend.agent.unified_ai_agent import generate_text, run_unified_ai
from backend.optimization.budget_optimizer import weekly_budget_planner
from backend.optimization.route_optimizer import optimize_route
from backend.services.location import get_user_location
from backend.services.store_finder import recommend_best_store
from backend.utils.sanitizers import clean_stores
from backend.db.recipe_cache_repository import list_recipes

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

DEFAULT_WEEKLY_MEALS = [
    "Tomato Pasta",
    "Vegetable Stir Fry",
    "Lentil Curry",
    "Rice Bowl",
    "Chickpea Salad",
    "Oatmeal Fruit Bowl",
    "Veggie Omelet",
    "Greek Yogurt Parfait",
    "Avocado Toast",
    "Breakfast Burrito",
    "Quinoa Breakfast Bowl",
    "Smoothie Bowl",
    "Black Bean Tacos",
    "Mediterranean Wrap",
    "Minestrone Soup",
    "Tofu Rice Bowl",
    "Pesto Pasta",
    "Stuffed Bell Peppers",
    "Vegetable Curry",
    "Bean Chili",
    "Teriyaki Noodles",
]

MEAL_TIMES = ["Breakfast", "Lunch", "Dinner"]


def _meal_slot(index: int) -> tuple[str, str]:
    day = DAYS[index // len(MEAL_TIMES)]
    meal_type = MEAL_TIMES[index % len(MEAL_TIMES)]
    return day, meal_type


def _fallback_weekly_meals(pantry_items: list[str], count: int = 21) -> list[dict[str, str]]:
    pantry_hint = ", ".join(pantry_items[:3]) if pantry_items else "basic staples"
    return [
        {
            "name": DEFAULT_WEEKLY_MEALS[index % len(DEFAULT_WEEKLY_MEALS)],
            "day": _meal_slot(index)[0],
            "meal_type": _meal_slot(index)[1],
            "reason": f"Works well with {pantry_hint}.",
        }
        for index in range(count)
    ]


def _parse_suggested_meals(text: str, pantry_items: list[str], count: int) -> list[dict[str, str]]:
    try:
        cleaned = (text or "").strip()
        if "```" in cleaned:
            cleaned = cleaned.split("```")[1]
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
        parsed = json.loads(cleaned)
        raw_meals = parsed.get("meals", parsed) if isinstance(parsed, dict) else parsed
        meals = []
        for raw in raw_meals or []:
            if isinstance(raw, str):
                name, reason = raw.strip(), "Suggested for the week."
                day, meal_type = "", ""
            elif isinstance(raw, dict):
                name = str(raw.get("name") or raw.get("meal") or "").strip()
                reason = str(raw.get("reason") or raw.get("why") or "Suggested for the week.").strip()
                day = str(raw.get("day") or "").strip()
                meal_type = str(raw.get("meal_type") or raw.get("mealType") or raw.get("type") or "").strip()
            else:
                continue
            if name:
                slot_day, slot_type = _meal_slot(len(meals))
                meals.append({"name": name, "day": day or slot_day, "meal_type": meal_type or slot_type, "reason": reason})
            if len(meals) >= count:
                break
        return meals or _fallback_weekly_meals(pantry_items, count)
    except Exception as e:
        print(f"[plan-my-week] meal suggestion parse failed: {e}")
        return _fallback_weekly_meals(pantry_items, count)


def _suggest_weekly_meals(pantry_items: list[str], dietary: str, count: int = 21) -> tuple[list[dict[str, str]], str]:
    prompt = f"""You are SmartCart's meal planning assistant.
Return ONLY valid JSON.
Suggest {count} practical meals for a full 7-day week: breakfast, lunch, and dinner for each day.
Use pantry context when helpful, but meals must still work if pantry is sparse.

Pantry items: {pantry_items}
Dietary preference: {dietary}

Output format:
{{"meals":[{{"name":"meal name","day":"Monday","meal_type":"Breakfast","reason":"brief reason under 80 chars"}}]}}
"""
    try:
        text = generate_text(prompt)
        return _parse_suggested_meals(text, pantry_items, count), "generated"
    except Exception as e:
        print(f"[plan-my-week] meal suggestion failed: {e}")
        return _fallback_weekly_meals(pantry_items, count), "fallback"



def _cached_meals_from_pantry(user_id: str, pantry_items: list[str], dietary: str, count: int) -> list[dict[str, str]]:
    pantry_set = set(_normalize_items(pantry_items))
    if not pantry_set:
        return []
    ranked = []
    for recipe in list_recipes(user_id):
        meal = str(recipe.get("meal", "")).split("|")[0].strip()
        ingredients = _normalize_items(recipe.get("ingredients", []))
        if not meal or not ingredients:
            continue
        overlap = len(set(ingredients) & pantry_set)
        if overlap:
            ranked.append((overlap, len(ingredients), meal, ingredients))
    ranked.sort(key=lambda row: (-row[0], row[1], row[2]))
    return [
        {"name": meal, "day": _meal_slot(index)[0], "meal_type": _meal_slot(index)[1], "reason": f"Reuses {overlap} pantry item(s) from saved recipes."}
        for index, (overlap, _size, meal, _ingredients) in enumerate(ranked[:count])
    ]

def _format_stores(store_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "store_name": r.get("store", {}).get("name"),
            "lat": r.get("store", {}).get("lat"),
            "lng": r.get("store", {}).get("lng"),
            "basket_price": r.get("score", {}).get("total_price", 0),
            "distance_km": r.get("score", {}).get("distance_km", 0),
            "final_score": r.get("score", {}).get("final_score", 0),
            "items": r.get("items", []),
            "price_breakdown": r.get("price_breakdown", {}),
        }
        for r in store_results[:3]
    ]


def _price_sources_from_stores(stores: list[dict[str, Any]], shopping_list: list[str]) -> dict[str, str]:
    sources = {item: "estimate" for item in shopping_list}
    for store in stores:
        for item, data in (store.get("price_breakdown") or {}).items():
            if isinstance(data, dict) and data.get("source") == "receipt":
                sources[item] = "receipt"
    return sources


def build_week_plan(
    user_id: str,
    *,
    budget: float = 100,
    dietary_instruction: str = "Vegetarian only",
    user_lat: float | None = None,
    user_lng: float | None = None,
    manual_city: str | None = None,
    manual_state: str | None = None,
    manual_postal_code: str | None = None,
    meal_count: int = 21,
    gemini_allowed: bool = True,
) -> dict[str, Any]:
    budget_value = float(budget)
    if budget_value < 0:
        raise ValueError("budget must be greater than or equal to 0")

    steps: list[dict[str, str]] = []
    print(f"[plan-my-week] starting user={user_id} budget={budget_value}")

    try:
        from backend.db.pantry_repository import get_pantry

        pantry_items = _normalize_items(get_pantry(user_id) or [])
        print(f"[plan-my-week] pantry checked: {len(pantry_items)} items")
        steps.append({
            "tool": "get_pantry",
            "status": "success",
            "summary": f"Checked pantry — found {len(pantry_items)} item(s)",
        })
    except Exception as e:
        print(f"[plan-my-week] pantry check failed: {e}")
        pantry_items = []
        steps.append({"tool": "get_pantry", "status": "error", "summary": "Pantry lookup unavailable — planning without pantry items"})

    cached_suggestions = _cached_meals_from_pantry(user_id, pantry_items, dietary_instruction, meal_count)
    if len(cached_suggestions) >= meal_count:
        suggested_meals, meal_source = cached_suggestions[:meal_count], "recipe_cache"
    else:
        generated_meals, meal_source = _suggest_weekly_meals(pantry_items, dietary_instruction, meal_count - len(cached_suggestions))
        seen = {meal["name"].lower() for meal in cached_suggestions}
        suggested_meals = cached_suggestions + [meal for meal in generated_meals if meal["name"].lower() not in seen]
        suggested_meals = suggested_meals[:meal_count]
        meal_source = "recipe_cache+" + meal_source if cached_suggestions else meal_source
    weekly_meals = {f"{meal.get('day') or _meal_slot(index)[0]} {meal.get('meal_type') or _meal_slot(index)[1]}": meal["name"] for index, meal in enumerate(suggested_meals)}
    steps.append({
        "tool": "generate_weekly_meals",
        "status": "success",
        "summary": f"Generated {len(suggested_meals)} meal suggestion(s) using {'pantry context' if pantry_items else 'default planning'}",
    })
    print(f"[plan-my-week] meals generated source={meal_source}: {weekly_meals}")

    try:
        ai_result = run_unified_ai(
            user_id=user_id,
            weekly_meals=weekly_meals,
            manual_items=[],
            dietary=dietary_instruction,
            force_refresh=False,
            gemini_allowed=gemini_allowed,
            cache_write_enabled=False,
        )
        full_shopping_list = _normalize_items(ai_result.get("shopping_list", []))
        print(f"[plan-my-week] raw shopping list built: {len(full_shopping_list)} items")
        if not full_shopping_list and weekly_meals:
            reason = ai_result.get("_error_message") or "Ingredient generation returned an empty shopping list"
            raise ValueError(reason)
    except Exception as e:
        print(f"[plan-my-week] ingredient generation failed: {e}")
        full_shopping_list = _normalize_items([meal["name"] for meal in suggested_meals])
        ai_result = {"substitutions": {}, "nutrition_report": {}, "_gemini_called": False, "_source": "fallback"}
        steps.append({"tool": "run_unified_ai", "status": "error", "summary": "Ingredient generation unavailable — using meal names as a basic list"})

    combined_shopping_list, pantry_items_used = _remove_pantry_items(full_shopping_list, pantry_items)
    steps.append({
        "tool": "remove_pantry_items",
        "status": "success",
        "summary": f"Built shopping list — {len(combined_shopping_list)} missing item(s), {len(pantry_items_used)} covered by pantry",
    })
    print(f"[plan-my-week] pantry-covered={len(pantry_items_used)} missing={len(combined_shopping_list)}")

    try:
        budget_summary = weekly_budget_planner(combined_shopping_list, budget_value)
        optimization = budget_summary.get("optimization", {}) or {}
        optimized_list = _normalize_items(optimization.get("optimized_list") or combined_shopping_list)
        steps.append({
            "tool": "weekly_budget_planner",
            "status": "success",
            "summary": f"Optimized budget — estimated savings ${float(optimization.get('money_saved', 0)):.2f}",
        })
    except Exception as e:
        print(f"[plan-my-week] budget optimization failed: {e}")
        budget_summary = {"optimization": {"optimized_list": combined_shopping_list, "original_cost": 0, "optimized_cost": 0, "money_saved": 0}}
        optimization = budget_summary["optimization"]
        optimized_list = combined_shopping_list
        steps.append({"tool": "weekly_budget_planner", "status": "error", "summary": "Budget optimization unavailable — keeping pantry-filtered list"})

    try:
        loc = get_user_location(
            user_lat=user_lat,
            user_lng=user_lng,
            manual_city=manual_city,
            manual_state=manual_state,
            manual_postal_code=manual_postal_code,
        ) or {}
        user_location = {
            "lat": loc.get("lat") or 0,
            "lng": loc.get("lng") or 0,
            "city": loc.get("city", ""),
            "region": loc.get("region", ""),
            "country": loc.get("country", ""),
        }
        store_results = clean_stores(recommend_best_store(user_location, optimized_list))
        stores = _format_stores(store_results)
        route = optimize_route([r.get("store", {}) for r in store_results[:3]], user_location)
        optimized_route = [
            {
                "stop": index,
                "store_name": store.get("name"),
                "lat": store.get("lat"),
                "lng": store.get("lng"),
                "distance_km": round(store.get("distance_km", 0), 1),
            }
            for index, store in enumerate(route, 1)
            if isinstance(store, dict)
        ]
        price_sources = _price_sources_from_stores(stores, optimized_list)
        if stores:
            budget_summary = weekly_budget_planner(
                optimized_list,
                budget_value,
                recommended_stores=stores,
            )
            optimization = budget_summary.get("optimization", {}) or {}
        steps.append({
            "tool": "recommend_best_store",
            "status": "success" if stores else "error",
            "summary": f"Compared prices across receipts and nearby stores — found {len(stores)} store option(s)",
        })
        print(f"[plan-my-week] pricing compared stores={len(stores)} sources={price_sources}")
    except Exception as e:
        print(f"[plan-my-week] store comparison failed: {e}")
        user_location = {}
        stores = []
        optimized_route = []
        price_sources = {item: "estimate" for item in optimized_list}
        steps.append({"tool": "recommend_best_store", "status": "error", "summary": "Nearby store lookup unavailable — using price estimates only"})

    return {
        "success": True,
        "suggested_meals": suggested_meals,
        "combined_shopping_list": optimized_list,
        "pantry_items_used": pantry_items_used,
        "original_total": round(float(optimization.get("original_cost", 0)), 2),
        "optimized_total": round(float(optimization.get("optimized_cost", 0)), 2),
        "estimated_savings": round(float(optimization.get("money_saved", 0)), 2),
        "price_sources": price_sources,
        "recommended_stores": stores,
        "optimized_route": optimized_route,
        "budget_summary": budget_summary,
        "nutrition_report": ai_result.get("nutrition_report", {}) or {},
        "weekly_meals": weekly_meals,
        "substitutions": ai_result.get("substitutions", {}) or {},
        "meal_ingredients": ai_result.get("meal_ingredients", {}) or {},
        "user_location": user_location,
        "steps": steps,
        "requires_approval": True,
        "generation_source": ai_result.get("_source", meal_source),
        "_gemini_called": bool(ai_result.get("_gemini_called", False)),
    }
