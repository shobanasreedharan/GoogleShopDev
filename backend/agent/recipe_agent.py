from typing import Dict, Any, List
import json
import os
from dotenv import load_dotenv

import vertexai
from vertexai.generative_models import GenerativeModel

from backend.db.recipe_cache_repository import (
    build_recipe_cache_key,
    get_cached_recipe,
    save_recipe_cache,
)

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")


# =====================================================
# INIT VERTEX AI (ADC AUTH)
# =====================================================

vertexai.init(
    project=PROJECT_ID,
    location="us-central1"
)

model = GenerativeModel(GEMINI_MODEL_NAME)


# =====================================================
# MAIN MEAL AI AGENT (NEW SINGLE PROMPT DESIGN)
# =====================================================

def generate_meal_plan(dish_name: str, dietary_instruction: str) -> Dict[str, Any]:
    """
    Single Gemini call that returns:
    - shopping list
    - nutrition report
    """

    user_id = os.getenv("DEFAULT_USER_ID", "demo_user")
    cache_key = build_recipe_cache_key(dish_name, dietary_instruction)

    # -------------------------
    # 1. CACHE CHECK
    # -------------------------
    cached = get_cached_recipe(user_id, cache_key)

    if cached:
        return cached

    # -------------------------
    # 2. GEMINI PROMPT (SINGLE SOURCE OF TRUTH)
    # -------------------------
    prompt = f"""
                    You are an AI grocery planning assistant.
                    
                    Task:
                    
                    Given a dish and dietary restrictions:
                    
                    Generate a complete shopping list.
                    Analyze the nutritional quality.
                    Suggest ingredient substitutions.
                    
                    Dish:
                    {dish_name}
                    
                    Dietary Rules:
                    {dietary_instruction}
                    
                    Return ONLY valid JSON.
                    
                    {
                    "shopping_list": [
                    "ingredient1",
                    "ingredient2"
                    ],
                    
                    "nutrition_report": {
                    "calories": 0,
                    "protein_g": 0,
                    "carbs_g": 0,
                    "fat_g": 0,
                    "fiber_g": 0,
                    "protein_score": 0,
                    "vegetable_score": 0,
                    "carb_score": 0,
                    "fat_score": 0,
                    "summary": "",
                    "strengths": [],
                    "weaknesses": [],
                    "recommendations": []
                    },
                    
                    "substitutions": {
                    "ingredient1": ["alt1", "alt2", "alt3"],
                    "ingredient2": ["alt1", "alt2", "alt3"]
                    }
                    }
"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # clean markdown if any
        text = text.replace("```json", "").replace("```", "").strip()

        data = json.loads(text)

        shopping_list = data.get("shopping_list", [])
        nutrition_report = data.get("nutrition_report", {})
        substitutions = data.get("substitutions", {})

        print("=== NUTRITION REPORT in recipe_agent===")
        print(nutrition_report)
        print("=========================")

        print("=== SUBSTITUTION in recipe_agent===")
        print(substitutions)
        print("=========================")

        if not isinstance(shopping_list, list):
            raise ValueError("Invalid shopping list format")

        cleaned_list = [
            str(i).lower().strip()
            for i in shopping_list
            if i
        ]

        result = {
            "shopping_list": sorted(set(cleaned_list)),
            "nutrition_report": nutrition_report,
            "substitutions" : substitutions
        }

        # -------------------------
        # 3. CACHE RESULT
        # -------------------------
        save_recipe_cache(
            user_id=user_id,
            meal=cache_key,
            ingredients=cleaned_list,
            nutrition=nutrition_report,
            substitutions=substitutions,
            source="vertex_ai",
        )

        return result

    except Exception as e:
        print(f"[recipe_agent] Gemini failed: {e}")

    # -------------------------
    # 4. FALLBACK
    # -------------------------
    return {
        "shopping_list": fallback_ingredients(dish_name),
        "nutrition_report": {
            "calories": 350,
            "protein_g": 350,
            "carbs_g": 350,
            "fat_g":350,
            "fiber_g": 200,
            "protein_score": 5,
            "vegetable_score": 5,
            "carb_score": 5,
            "fat_score": 5,
            "summary": "Fallback nutrition analysis used",
            "strengths": [],
            "weaknesses": [],
            "recommendations": []
        }
    }


# =====================================================
# FALLBACK ENGINE
# =====================================================

def fallback_ingredients(dish_name: str) -> List[str]:
    base = {
        "pasta": ["pasta", "tomato", "garlic", "olive oil"],
        "biryani": ["rice", "spices", "onion", "yogurt"],
        "salad": ["lettuce", "cucumber", "olive oil"],
        "stir fry": ["vegetables", "soy sauce", "garlic"],
        "pizza": ["dough", "cheese", "tomato sauce"],
    }

    for key, value in base.items():
        if key in dish_name.lower():
            return value

    return ["rice", "vegetables", "salt"]


# =====================================================
# PUBLIC API
# =====================================================

def run_recipe_agent(
    user_prompt: str,
    dietary_instruction: str = "Vegetarian only"
) -> Dict[str, Any]:

    if not user_prompt or not user_prompt.strip():
        return {"shopping_list": [],
                "nutrition_report": {},
                "substitutions": {}}

    return generate_meal_plan(user_prompt, dietary_instruction)