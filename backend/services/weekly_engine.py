from typing import Dict, List, Any
import json
import os
import vertexai
from vertexai.generative_models import GenerativeModel
from dotenv import load_dotenv

from backend.db.recipe_cache_repository import (
    get_cached_recipe,
    save_recipe_cache
)

from backend.ai.fallback_engine import fallback_ingredients

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")

# =====================================================
# INIT ONCE
# =====================================================
if PROJECT_ID:
    vertexai.init(project=PROJECT_ID, location="us-central1")

model = GenerativeModel(GEMINI_MODEL_NAME)


# =====================================================
# PROMPT
# =====================================================
def _build_prompt(meal: str, dietary_instruction: str) -> str:
    return f"""
You are a chef + nutrition AI.

Return ONLY valid JSON:

{{
  "ingredients": ["item1", "item2"],
  "nutrition_report": {{
    "calories": 0,
    "protein_g": 0,
    "carbs_g": 0,
    "fat_g": 0,
    "fiber_g": 0,
    "protein_score": 0,
    "vegetable_score": 0,
    "carb_score": 0,
    "fat_score": 0,
    "summary": "short explanation",
    "strengths": [],
    "weaknesses": [],
    "recommendations": []
  }}
}}

Meal: {meal}
Dietary: {dietary_instruction}
"""


# =====================================================
# SAFE PARSER
# =====================================================
def _safe_json(text: str):
    try:
        text = text.strip()

        if "```" in text:
            text = text.split("```")[1]
            if text.lower().startswith("json"):
                text = text[4:].strip()

        return json.loads(text)

    except Exception:
        return None


# =====================================================
# CORE ENGINE
# =====================================================
def build_weekly_ingredients_batched(
    weekly_meals: Dict[str, str],
    dietary_instruction: str = "Vegetarian only"
) -> Dict[str, Any]:

    result: Dict[str, Any] = {}

    for day, meal in weekly_meals.items():

        cache_key = f"{meal.lower().strip()}|{dietary_instruction.lower().strip()}"

        cached = get_cached_recipe(cache_key)

        if cached and isinstance(cached, dict):
            result[day] = cached
            continue

        try:
            prompt = _build_prompt(meal, dietary_instruction)
            response = model.generate_content(prompt)

            parsed = _safe_json(response.text)

            if not isinstance(parsed, dict):
                raise ValueError("Invalid AI response")

            ingredients = [
                str(i).lower().strip()
                for i in parsed.get("ingredients", [])
                if i
            ]

            nutrition = parsed.get("nutrition_report", {}) or {}

            output = {
                "ingredients": ingredients,
                "nutrition_report": nutrition
            }

            result[day] = output

            save_recipe_cache(
                meal=cache_key,
                ingredients=ingredients,
                source="gemini",
                nutrition=nutrition
            )

        except Exception as e:
            print(f"[weekly_engine] AI failed for {meal}: {e}")

            fallback = fallback_ingredients(meal)

            result[day] = {
                "ingredients": fallback,
                "nutrition_report": {
                    "summary": "fallback mode",
                    "calories": 0,
                    "protein_g": 0,
                    "carbs_g": 0,
                    "fat":0,
                    "fiber_g": 0,
                    "protein_score": 0,
                    "vegetable_score": 0,
                    "carb_score": 0,
                    "fat_score": 0,
                    "strengths": [],
                    "weaknesses": [],
                    "recommendations": []
                }
            }

    return result


# =====================================================
# MERGE
# =====================================================
def merge_ingredients(data: Dict[str, Any]) -> List[str]:
    merged = set()

    for day_data in data.values():
        if isinstance(day_data, dict):
            for item in day_data.get("ingredients", []):
                if item:
                    merged.add(str(item).lower().strip())

    return sorted(merged)


# =====================================================
# CATEGORY
# =====================================================
CATEGORY_MAP = {
    "vegetables": ["tomato", "onion", "garlic", "spinach", "carrot"],
    "dairy": ["milk", "cheese", "butter", "cream"],
    "protein": ["tofu", "beans", "lentils", "chicken"],
    "grains": ["rice", "pasta", "bread"],
    "fats": ["oil", "butter", "avocado"],
}


def group_ingredients(ingredients: List[str]) -> Dict[str, List[str]]:
    categories = {k: [] for k in CATEGORY_MAP}
    categories["others"] = []

    for item in ingredients:
        placed = False

        for cat, keywords in CATEGORY_MAP.items():
            if any(k in item for k in keywords):
                categories[cat].append(item)
                placed = True
                break

        if not placed:
            categories["others"].append(item)

    return categories


# =====================================================
# PUBLIC API (FIXED OUTPUT SHAPE)
# =====================================================
def run_weekly_engine(
    weekly_meals: Dict[str, str],
    dietary_instruction: str = "Vegetarian only"
) -> Dict[str, Any]:

    weekly_data = build_weekly_ingredients_batched(
        weekly_meals,
        dietary_instruction
    )

    merged = merge_ingredients(weekly_data)
    grouped = group_ingredients(merged)

    nutrition_reports = {
        day: data.get("nutrition_report", {})
        for day, data in weekly_data.items()
        if isinstance(data, dict)
    }

    return {
        "weekly_breakdown": weekly_data,
        "shopping_list": merged,
        "categorized_list": grouped,
        "nutrition_reports": nutrition_reports
    }