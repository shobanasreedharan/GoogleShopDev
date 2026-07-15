from typing import Any, Dict

from backend.db.pantry_repository import get_pantry, save_pantry
from backend.db.meal_plan_repository import save_meal_plan
from backend.db.recipe_cache_repository import (
    get_cached_recipe,
    save_recipe_cache
)


class MongoTools:
    """
    Clean MCP Tool (Registry-Compatible)
    NOTE: name kept as "mongo" for registry compatibility — underlying
    storage is now Firestore. Rename later if you want to do a clean sweep.
    """

    TOOL_NAME = "mongo"

    def name(self) -> str:
        return self.TOOL_NAME

    # =====================================================
    # ENTRYPOINT (USED BY REGISTRY)
    # =====================================================

    def execute(self, action: str, payload: Dict[str, Any]) -> Any:

        routes = {
            "get_pantry": self._get_pantry,
            "save_meal_plan": self._save_meal_plan,
            "get_recipe_cache": self._get_recipe_cache,
            "save_recipe_cache": self._save_recipe_cache,
            "update_pantry": self._update_pantry,
        }

        handler = routes.get(action)

        if not handler:
            raise ValueError(f"Unknown action: {action}")

        return handler(payload)

    # =====================================================
    # TOOLS
    # =====================================================

    def _get_pantry(self, payload: Dict[str, Any]) -> dict:
        user_id = payload.get("user_id")
        if not user_id:
            raise ValueError("user_id is required")

        items = get_pantry(user_id)

        return {
            "user_id": user_id,
            "items": items or [],
            "count": len(items or [])
        }

    def _save_meal_plan(self, payload: Dict[str, Any]) -> dict:
        return save_meal_plan(
            user_id=payload["user_id"],
            weekly_meals=payload["weekly_meals"],
            shopping_list=payload["shopping_list"],
            budget_summary=payload.get("budget_summary", {}),
            nutrition_report=payload.get("nutrition_report", {}),
        )

    def _get_recipe_cache(self, payload: Dict[str, Any]) -> dict:
        user_id = payload.get("user_id")
        meal = payload.get("meal")
        if not user_id:
            raise ValueError("user_id is required")
        if not meal:
            raise ValueError("meal is required")

        return get_cached_recipe(user_id, meal)

    def _save_recipe_cache(self, payload: Dict[str, Any]) -> dict:
        user_id = payload.get("user_id")
        if not user_id:
            raise ValueError("user_id is required")

        return save_recipe_cache(
            user_id=user_id,
            meal=payload["meal"],
            ingredients=payload["ingredients"],
            source=payload.get("source", "vertex_ai"),
        )

    def _update_pantry(self, payload: Dict[str, Any]) -> dict:
        user_id = payload.get("user_id")
        if not user_id:
            raise ValueError("user_id is required")
        items = payload.get("items", [])
        return save_pantry(user_id, items)
