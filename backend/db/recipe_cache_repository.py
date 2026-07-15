from datetime import datetime
from backend.db.firestore_client import db

# =====================================================
# LIMITS (enforced server-side)
# =====================================================
MAX_INGREDIENTS = 20
MAX_INGREDIENT_LEN = 50
MAX_STEPS = 8
MAX_STEP_LEN = 100


def _sanitize_doc_id(raw: str) -> str:
    safe = raw.replace("/", "_").strip()
    return safe or "unknown"


def _cache_collection(user_id: str):
    return db.collection("users").document(user_id).collection("recipe_cache")


def _enforce_limits(ingredients: list, instructions: list):
    """Server-side enforcement — never trust client."""
    clean_ingredients = [
        str(i).strip()[:MAX_INGREDIENT_LEN]
        for i in (ingredients or [])
        if str(i).strip()
    ][:MAX_INGREDIENTS]

    clean_instructions = [
        str(s).strip()[:MAX_STEP_LEN]
        for s in (instructions or [])
        if str(s).strip()
    ][:MAX_STEPS]

    return clean_ingredients, clean_instructions


# =====================================================
# GET SINGLE RECIPE
# =====================================================
def get_cached_recipe(user_id: str, meal: str):
    if not meal:
        return None
    doc_id = _sanitize_doc_id(meal)
    doc = _cache_collection(user_id).document(doc_id).get()
    if not doc.exists:
        return None
    return doc.to_dict()


# =====================================================
# LIST ALL RECIPES FOR USER
# =====================================================
def list_recipes(user_id: str) -> list:
    """Returns all saved recipes for the user, sorted by meal name."""
    try:
        docs = _cache_collection(user_id).order_by("meal").stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print(f"ERROR listing recipes for {user_id}: {e}")
        return []


# =====================================================
# SAVE / UPDATE RECIPE
# =====================================================
def save_recipe_cache(
    user_id: str,
    meal: str,
    ingredients: list,
    source: str,
    nutrition: dict = None,
    substitutions: dict = None,
    instructions: list = None,
):
    meal = " ".join(meal.strip().lower().split())
    if nutrition is None:
        nutrition = {}
    if substitutions is None:
        substitutions = {}

    clean_ingredients, clean_instructions = _enforce_limits(ingredients, instructions)

    doc_id = _sanitize_doc_id(meal)
    print(f"save recipe cache: {meal} (user={user_id})")

    try:
        _cache_collection(user_id).document(doc_id).set({
            "meal":             meal,
            "ingredients":      clean_ingredients,
            "instructions":     clean_instructions,
            "source":           source,
            "nutrition_report": nutrition,
            "substitutions":    substitutions,
            "updated_at":       datetime.utcnow(),
        })
        print(f"saved recipe cache: {meal} — {len(clean_ingredients)} ingredients, {len(clean_instructions)} instructions")

    except Exception as e:
        print(f"ERROR saving recipe cache for {meal}: {e}")


# =====================================================
# USER SAVE (from Recipe page — preserves AI nutrition)
# =====================================================
def user_save_recipe(
    user_id: str,
    meal: str,
    ingredients: list,
    instructions: list,
):
    """
    Called when a user manually saves/edits a recipe from the UI.
    Merges with existing doc to preserve nutrition_report and substitutions.
    """
    meal = " ".join(meal.strip().lower().split())
    clean_ingredients, clean_instructions = _enforce_limits(ingredients, instructions)
    doc_id = _sanitize_doc_id(meal)

    try:
        _cache_collection(user_id).document(doc_id).set({
            "meal":        meal,
            "ingredients": clean_ingredients,
            "instructions": clean_instructions,
            "source":      "user_saved",
            "updated_at":  datetime.utcnow(),
        }, merge=True)  # merge=True preserves nutrition_report, substitutions
        print(f"user saved recipe: {meal} ({len(clean_ingredients)} ingredients, {len(clean_instructions)} instructions)")
        return {"meal": meal, "ingredients": clean_ingredients, "instructions": clean_instructions}

    except Exception as e:
        print(f"ERROR user saving recipe for {meal}: {e}")
        raise


# =====================================================
# SAFE NORMALIZER
# =====================================================
def normalize_cache(doc: dict):
    if not doc:
        return None
    return {
        "ingredients":      doc.get("ingredients", []),
        "instructions":            doc.get("instructions", []),
        "nutrition_report": doc.get("nutrition_report", {}),
    }
