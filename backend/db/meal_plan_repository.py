from datetime import datetime
from backend.db.firestore_client import db


def _sanitize_doc_id(raw: str) -> str:
    safe = raw.replace("/", "_").strip()
    return safe or "manual"


def save_meal_plan(
    user_id:          str,
    weekly_meals:     dict,
    shopping_list:    list,
    budget_summary:   dict = {},
    nutrition_report: dict = {},
):
    """
    Saves or updates a meal plan in Firestore.
    Matches on normalized meal-name key to prevent duplicates,
    scoped under the user's own document.
    Called after every /generate and /regenerate request.
    """

    meal_names = sorted([
        " ".join(str(v).strip().lower().split())
        for v in (weekly_meals or {}).values()
        if v
    ])
    meal_key = _sanitize_doc_id("|".join(meal_names) if meal_names else "manual")

    document = {
        "user_id":          user_id,
        "meal_key":         meal_key,
        "updated_at":       datetime.utcnow(),
        "weekly_meals":     weekly_meals,
        "shopping_list":    shopping_list,
        "budget_summary":   budget_summary,
        "nutrition_report": nutrition_report,
        "total_cost":       budget_summary.get("optimization", {}).get("optimized_cost", 0),
        "money_saved":      budget_summary.get("optimization", {}).get("money_saved", 0),
    }

    doc_ref = (
        db.collection("users")
        .document(user_id)
        .collection("meal_plans")
        .document(meal_key)
    )
    doc_ref.set(document, merge=True)
    return document


def list_meal_plan_recipes(user_id: str) -> list:
    """Return unique meal names saved under users/{uid}/meal_plans."""
    seen = set()
    meals = []
    docs = (
        db.collection("users")
        .document(user_id)
        .collection("meal_plans")
        .stream()
    )
    for doc in docs:
        data = doc.to_dict() or {}
        for meal in (data.get("weekly_meals") or {}).values():
            normalized = " ".join(str(meal).strip().split())
            key = normalized.lower()
            if normalized and key not in seen:
                seen.add(key)
                meals.append(normalized)
    return meals


def save_generated_meal_recipe(user_id: str, day: str, meal: str):
    """Save one newly generated meal as a reusable meal_plan recipe."""
    normalized = " ".join(str(meal).strip().split())
    if not normalized:
        return None
    return save_meal_plan(
        user_id=user_id,
        weekly_meals={day: normalized},
        shopping_list=[],
        budget_summary={},
        nutrition_report={},
    )
