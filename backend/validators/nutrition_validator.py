from pydantic import ValidationError
from backend.schemas.nutrition import NutritionReport, NutritionScores, AIFeedback


def validate_nutrition(data: dict) -> dict:
    if not data:
        data = {}

    print(f"[nutrition] raw data from Gemini: {data}")  # DEBUG — remove after fix
    # Auto-detect flat Gemini response and reshape to nested schema
    # Gemini returns: { "calories": 500, "protein_g": 20, "summary": "...", ... }
    # Schema expects: { "nutrition_scores": {...}, "ai_feedback": {...} }
    if "nutrition_scores" not in data:
        data = {
            "nutrition_scores": {
                "calories":        data.get("calories",        0),
                "protein_g":       data.get("protein_g",       0),
                "carbs_g":         data.get("carbs_g",         0),
                "fat_g":           data.get("fat_g",           0),
                "fiber_g":         data.get("fiber_g",         0),
                "protein_score":   data.get("protein_score",   0),
                "vegetable_score": data.get("vegetable_score", 0),
                "carb_score":      data.get("carb_score",      0),
                "fat_score":       data.get("fat_score",       0),
                "health_rating":   data.get("health_rating",   "—"),
            },
            "ai_feedback": {
                "summary":         data.get("summary",         ""),
                "strengths":       data.get("strengths",       []),
                "weaknesses":      data.get("weaknesses",      []),
                "recommendations": data.get("recommendations", []),
            }
        }

    try:
        # ✅ Try to enforce strict schema
        return NutritionReport(**data).model_dump()

    except ValidationError as e:
        print("[NUTRITION VALIDATION FAILED]", e)

        # 🛟 SAFE FALLBACK (never break UI)
        return NutritionReport(
            nutrition_scores=NutritionScores(
                calories=0, protein_g=0, carbs_g=0,
                fat_g=0, fiber_g=0, protein_score=0,
                vegetable_score=0, carb_score=0,
                fat_score=0, health_rating="—"
            ),
            ai_feedback=AIFeedback()
        ).model_dump()