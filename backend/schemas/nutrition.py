# backend/schemas/nutrition.py

from pydantic import BaseModel
from typing import List, Dict

class NutritionScores(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    protein_score: int
    vegetable_score: int
    carb_score: int
    fat_score: int
    health_rating: str = "—"


class AIFeedback(BaseModel):
    summary: str = ""
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendations: List[str] = []


class NutritionReport(BaseModel):
    nutrition_scores: NutritionScores
    ai_feedback: AIFeedback