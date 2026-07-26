from typing import Dict, Any
import json
import os
from dotenv import load_dotenv

from backend.core.gpt56_client import generate_primary_or_fallback
from backend.db.recipe_cache_repository import (
    build_recipe_cache_key,
    get_cached_recipe,
    save_recipe_cache
)

load_dotenv()


def _generate_with_gemini(prompt: str) -> str:
    """Keep the established Gemini generation path available as a fallback."""
    from vertexai.generative_models import GenerativeModel

    model = GenerativeModel(os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash"))
    return model.generate_content(prompt).text


def generate_text(prompt: str) -> str:
    """Multi-meal planning uses Gemini directly (GPT-5.6 integration is scoped to chat and single-meal only)."""
    return _generate_with_gemini(prompt)


def _cache_key(meal: str, dietary: str) -> str:
    return build_recipe_cache_key(meal, dietary)


def _meal_type_from_slot(slot: str) -> str:
    normalized = " ".join((slot or "").strip().lower().split())
    for meal_type in ("breakfast", "lunch", "dinner"):
        if meal_type in normalized.split():
            return meal_type
    return normalized if normalized in {"breakfast", "lunch", "dinner"} else ""


def _build_single_meal_prompt(weekly_meals: dict, dietary: str, manual_items: list) -> str:
    return f"""
You are a world-class grocery planning AI.
You MUST return ONLY valid JSON.

TASK: Generate shopping list, nutrition analysis, smart substitutions, and step-by-step cooking instructions.

INPUT:
Weekly meals: {weekly_meals}
Manual items: {manual_items}
Dietary rule: {dietary}

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "shopping_list": ["item1", "item2"],
  "instructions": [
    "Step 1: <action under 100 chars>",
    "Step 2: <action under 100 chars>"
  ],
  "nutrition_report": {{
    "calories": <integer>,
    "protein_g": <integer>,
    "carbs_g": <integer>,
    "fat_g": <integer>,
    "fiber_g": <integer>,
    "protein_score": <0-10>,
    "vegetable_score": <0-10>,
    "carb_score": <0-10>,
    "fat_score": <0-10>,
    "health_rating": "<Good|Excellent|Fair>",
    "summary": "<2-3 sentences>",
    "strengths": ["<strength1>"],
    "weaknesses": ["<weakness1>"],
    "recommendations": ["<rec1>"]
  }},
  "substitutions": {{
    "item1": ["alt1", "alt2"]
  }}
}}

INSTRUCTIONS RULES:
- Maximum 8 instructions total
- Each step must be under 100 characters
- Action verbs only (Sauté, Boil, Mix, Add, Cook, Serve)
- No tips, no explanations, just the action

RULES: Follow dietary rule strictly. No markdown. No explanation. Valid JSON ONLY.
"""


def _build_multi_meal_prompt(weekly_meals: dict, dietary: str) -> str:
    meal_list = list(weekly_meals.values())
    return f"""
You are a world-class grocery planning AI.
You MUST return ONLY valid JSON.

TASK: For EACH meal listed, generate its own ingredient list and cooking instructions separately.
Then generate a combined nutrition analysis and substitutions for the whole week.

INPUT:
Meals: {meal_list}
Dietary rule: {dietary}

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "meals": {{
    "<meal_name_exactly_as_given>": {{
      "ingredients": ["ingredient1", "ingredient2"],
      "instructions": [
        "Step 1: <action under 100 chars>",
        "Step 2: <action under 100 chars>"
      ]
    }}
  }},
  "nutrition_report": {{
    "calories": <integer>,
    "protein_g": <integer>,
    "carbs_g": <integer>,
    "fat_g": <integer>,
    "fiber_g": <integer>,
    "protein_score": <0-10>,
    "vegetable_score": <0-10>,
    "carb_score": <0-10>,
    "fat_score": <0-10>,
    "health_rating": "<Good|Excellent|Fair>",
    "summary": "<2-3 sentences>",
    "strengths": ["<strength1>"],
    "weaknesses": ["<weakness1>"],
    "recommendations": ["<rec1>"]
  }},
  "substitutions": {{
    "item1": ["alt1", "alt2"]
  }}
}}

INSTRUCTIONS RULES:
- Maximum 8 instructions per meal
- Each step must be under 100 characters
- Action verbs only. No tips or explanations.

RULES: Each meal key must match the meal name exactly as given. Follow dietary rule strictly. No markdown. No explanation. Valid JSON ONLY.
"""


MULTI_MEAL_BATCH_SIZE = 5


def _batch_items(items: dict[str, str], size: int = MULTI_MEAL_BATCH_SIZE):
    entries = list(items.items())
    for index in range(0, len(entries), size):
        yield dict(entries[index:index + size])


def _format_response(parsed: dict, source: str = "gemini") -> Dict[str, Any]:
    nr = parsed.get("nutrition_report", {})
    if "nutrition_scores" in nr:
        nutrition_report = nr
    else:
        nutrition_report = {
            "nutrition_scores": {
                "calories":        nr.get("calories",        0),
                "protein_g":       nr.get("protein_g",       0),
                "carbs_g":         nr.get("carbs_g",         0),
                "fat_g":           nr.get("fat_g",           0),
                "fiber_g":         nr.get("fiber_g",         0),
                "protein_score":   nr.get("protein_score",   0),
                "vegetable_score": nr.get("vegetable_score", 0),
                "carb_score":      nr.get("carb_score",      0),
                "fat_score":       nr.get("fat_score",       0),
                "health_rating":   nr.get("health_rating",   "auto"),
            },
            "ai_feedback": {
                "summary":         nr.get("summary",         ""),
                "strengths":       nr.get("strengths",       []),
                "weaknesses":      nr.get("weaknesses",      []),
                "recommendations": nr.get("recommendations", []),
            }
        }
    return {
        "shopping_list":    parsed.get("shopping_list", []),
        "nutrition_report": nutrition_report,
        "substitutions":    parsed.get("substitutions", {}),
        "_source":          source,
    }


def run_unified_ai(
    user_id: str,
    weekly_meals: dict,
    manual_items: list = None,
    dietary: str = "Vegetarian only",
    force_refresh: bool = False,
    gemini_allowed: bool = True,
    cache_write_enabled: bool = True,
) -> Dict[str, Any]:

    manual_items = manual_items or []
    is_single_meal = len(weekly_meals) == 1

    # ─── SHOPPING LIST / MANUAL ITEMS ONLY (no meals at all) ───────────────────
    # This mode has zero entries in weekly_meals — previously this fell through
    # to the multi-meal branch below, which assumes at least one meal exists
    # (e.g. `list(weekly_meals.values())[0]` for a nutrition fallback), causing
    # "list index out of range". There's no meal to plan around here, so we
    # short-circuit with the manual items as the shopping list directly.
    if not weekly_meals:
        print("[unified_ai] No meals provided — manual items only (Shopping List mode)")
        shopping_list = list(dict.fromkeys(
            item.lower().strip() for item in manual_items
            if isinstance(item, str) and item.strip()
        ))
        result = _fallback(shopping_list)
        result["_source"] = "manual_items"
        result["_gemini_called"] = False
        result["instructions"] = []
        return result

    # ─── SINGLE MEAL ─────────────────────────────────────────────────────────
    if is_single_meal:
        meal_slot, meal = next(iter(weekly_meals.items()))
        meal_type = _meal_type_from_slot(meal_slot)
        key  = _cache_key(meal, dietary)

        # Cache check
        if not force_refresh:
            cached = get_cached_recipe(user_id, key)
            if cached:
                ingredients   = cached.get("ingredients") or cached.get("shopping_list", [])
                substitutions = cached.get("substitutions", {})
                nutrition     = cached.get("nutrition_report", {})
                instructions  = cached.get("instructions", [])
                if ingredients:
                    print(f"[unified_ai] Full cache hit: '{key}' — skipping Gemini")
                    result = _format_response({
                        "shopping_list":    ingredients,
                        "substitutions":    substitutions,
                        "nutrition_report": nutrition,
                    }, source="cache")
                    result["instructions"]    = instructions
                    result["_gemini_called"]  = False
                    return result
                print(f"[unified_ai] Partial cache hit: '{key}' — calling Gemini")

        # GPT-5.6 is primary here; retain Gemini as the resilience fallback.
        prompt = _build_single_meal_prompt(weekly_meals, dietary, manual_items)
        try:
            def generate_fallback(single_meal_prompt: str) -> str:
                if not gemini_allowed:
                    raise RuntimeError("Gemini limit reached")
                return _generate_with_gemini(single_meal_prompt)

            text, model_used = generate_primary_or_fallback(
                prompt,
                generate_fallback,
                log_prefix="unified_ai",
            )
            if "```" in text:
                text = text.split("```")[1]
                if text.lower().startswith("json"):
                    text = text[4:]
                text = text.strip()
            parsed = json.loads(text)
            result = _format_response(parsed, source=model_used)

            shopping_list = [item.lower() for item in result["shopping_list"]]
            if not shopping_list:
                raise ValueError("single-meal generation returned an empty shopping list")
            instructions  = parsed.get("instructions", [])

            if shopping_list and cache_write_enabled:
                save_recipe_cache(
                    user_id=user_id,
                    meal=key,
                    ingredients=shopping_list,
                    source=model_used,
                    nutrition=result["nutrition_report"],
                    substitutions=result.get("substitutions", {}),
                    instructions=instructions,
                    meal_type=meal_type,
                )
                print(f"[unified_ai] Cached: '{meal}' with {len(instructions)} instructions (user={user_id})")

            result["shopping_list"]  = shopping_list
            result["instructions"]   = instructions
            result["_gemini_called"] = model_used == "gemini"
            return result

        except Exception as e:
            print(f"[unified_ai] Single-meal generation failed; using deterministic meal fallback: {e}")
            return _single_meal_fallback(meal, manual_items)

    # ─── MULTI MEAL ──────────────────────────────────────────────────────────
    cached_meals:   dict[str, list] = {}
    uncached_meals: dict[str, str]  = {}

    if not force_refresh:
        for day, meal in weekly_meals.items():
            key    = _cache_key(meal, dietary)
            cached = get_cached_recipe(user_id, key)
            if cached and cached.get("ingredients"):
                cached_meals[meal] = cached["ingredients"]
                print(f"[unified_ai] Cache hit: '{meal}'")
            else:
                uncached_meals[day] = meal
                print(f"[unified_ai] Cache miss: '{meal}' — will call Gemini")
    else:
        uncached_meals = dict(weekly_meals)

    gemini_meals:     dict[str, list] = {}
    nutrition_report: dict            = {}
    substitutions:    dict            = {}
    gemini_called                     = False

    if uncached_meals and gemini_allowed:
        batches = list(_batch_items(uncached_meals))
        print(f"[unified_ai] Processing {len(uncached_meals)} uncached meals in {len(batches)} batch(es) of up to {MULTI_MEAL_BATCH_SIZE}")
        for batch_index, batch_meals in enumerate(batches, 1):
            prompt = _build_multi_meal_prompt(batch_meals, dietary)
            try:
                print(f"[unified_ai] Gemini batch {batch_index}/{len(batches)} starting with {len(batch_meals)} meal(s)")
                text = generate_text(prompt).strip()
                if "```" in text:
                    text = text.split("```")[1]
                    if text.lower().startswith("json"):
                        text = text[4:]
                    text = text.strip()
                parsed = json.loads(text)

                meals_data = parsed.get("meals", {})
                if not nutrition_report:
                    nutrition_report = parsed.get("nutrition_report", {})
                substitutions.update(parsed.get("substitutions", {}) or {})

                print(f"[unified_ai] Gemini batch {batch_index}/{len(batches)} returned meal keys: {list(meals_data.keys())}")
                print(f"[unified_ai] Gemini batch {batch_index}/{len(batches)} expected meal names: {list(batch_meals.values())}")

                for day, meal in batch_meals.items():
                    meal_data = meals_data.get(meal) or next(
                        (v for k, v in meals_data.items() if k.lower() == meal.lower()), {}
                    )
                    if isinstance(meal_data, list):
                        ingredients  = [str(i).lower().strip() for i in meal_data if str(i).strip()]
                        instructions = []
                    else:
                        ingredients  = [str(i).lower().strip() for i in meal_data.get("ingredients", []) if str(i).strip()]
                        instructions = meal_data.get("instructions", [])

                    if ingredients:
                        gemini_meals[meal] = ingredients
                    else:
                        print(f"[unified_ai] Gemini batch {batch_index}/{len(batches)} missing ingredients for '{meal}'")

                    if ingredients and cache_write_enabled:
                        key = _cache_key(meal, dietary)
                        save_recipe_cache(
                            user_id=user_id,
                            meal=key,
                            ingredients=ingredients,
                            source="gemini",
                            nutrition=_format_response(parsed)["nutrition_report"],
                            substitutions=substitutions,
                            instructions=instructions,
                            meal_type=_meal_type_from_slot(day),
                        )
                        print(f"[unified_ai] Cached: '{meal}' with {len(instructions)} instructions (user={user_id})")

                gemini_called = True

            except Exception as e:
                print(f"[unified_ai] Gemini failed (multi) batch {batch_index}/{len(batches)}: {e}")
                continue

    elif uncached_meals and not gemini_allowed:
        print(f"[unified_ai] Gemini limit reached — skipping {len(uncached_meals)} uncached meals")

    # Merge cached + gemini into combined shopping list
    all_meals = {**cached_meals, **gemini_meals}
    combined_shopping_list = list(dict.fromkeys(
        item for ingredients in all_meals.values() for item in ingredients
    ))
    print(f"[unified_ai] Final combined shopping list length after batching: {len(combined_shopping_list)}")

    if not nutrition_report and weekly_meals:
        first_meal   = list(weekly_meals.values())[0]
        first_key    = _cache_key(first_meal, dietary)
        first_cached = get_cached_recipe(user_id, first_key)
        nutrition_report = first_cached.get("nutrition_report", {}) if first_cached else {}

    result = _format_response({
        "shopping_list":    combined_shopping_list,
        "nutrition_report": nutrition_report,
        "substitutions":    substitutions,
    }, source="cache+gemini" if cached_meals else "gemini")

    result["meal_ingredients"] = all_meals
    result["_gemini_called"] = gemini_called
    if weekly_meals and not combined_shopping_list:
        result["_error"] = "empty_multi_meal_shopping_list"
        result["_error_message"] = "Multi-meal generation returned an empty shopping list"
    return result


def _single_meal_fallback(meal: str, manual_items: list) -> Dict[str, Any]:
    normalized_meal = " ".join(str(meal or "").strip().lower().split())
    known_recipe_ingredients = {
        "sambar idli": [
            "idli rice",
            "urad dal",
            "fenugreek seeds",
            "salt",
            "water",
            "toor dal",
            "onion",
            "tomato",
            "carrot",
            "potato",
            "drumstick pieces",
            "green chilies",
            "sambar powder",
            "turmeric",
            "tamarind",
            "oil",
        ],
        "idli sambar": [
            "idli rice",
            "urad dal",
            "fenugreek seeds",
            "salt",
            "water",
            "toor dal",
            "onion",
            "tomato",
            "carrot",
            "potato",
            "drumstick pieces",
            "green chilies",
            "sambar powder",
            "turmeric",
            "tamarind",
            "oil",
        ],
    }
    if normalized_meal in known_recipe_ingredients:
        base_items = known_recipe_ingredients[normalized_meal]
    elif "sambar" in normalized_meal and "idli" in normalized_meal:
        base_items = known_recipe_ingredients["sambar idli"]
    else:
        meal_words = [
            word.strip().lower()
            for word in normalized_meal.replace("/", " ").replace("-", " ").split()
            if word.strip()
        ]
        base_items = meal_words or [normalized_meal or "meal"]

    shopping_list = list(dict.fromkeys([
        *base_items,
        *(str(item).strip().lower() for item in (manual_items or []) if str(item).strip()),
    ]))
    result = _fallback(shopping_list)
    result["instructions"] = [
        f"Prepare {meal}"[:100],
        "Cook until ready",
        "Serve warm",
    ]
    result["_source"] = "single_meal_fallback"
    result["_gemini_called"] = False
    return result


def _fallback(manual_items: list) -> Dict[str, Any]:
    return {
        "shopping_list": manual_items,
        "nutrition_report": {
            "nutrition_scores": {
                "calories": 0, "protein_g": 0, "carbs_g": 0,
                "fat_g": 0, "fiber_g": 0, "protein_score": 0,
                "vegetable_score": 0, "carb_score": 0,
                "fat_score": 0, "health_rating": "—"
            },
            "ai_feedback": {
                "summary": "AI unavailable.",
                "strengths": [], "weaknesses": [],
                "recommendations": ["Try again in a few minutes"]
            }
        },
        "substitutions": {},
        "_source": "fallback"
    }
