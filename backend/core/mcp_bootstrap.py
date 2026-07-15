from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import TransportSecuritySettings
from backend.db.pantry_repository import get_pantry, save_pantry
from backend.db.meal_plan_repository import save_meal_plan
from backend.db.recipe_cache_repository import get_cached_recipe, save_recipe_cache

mcp = FastMCP(
    "smartcart-mcp",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
)

@mcp.tool()
def ping() -> dict:
    return {"status": "ok"}

@mcp.tool()
def get_pantry_items(user_id: str) -> dict:
    items = get_pantry(user_id)
    return {"user_id": user_id, "items": items or [], "count": len(items or [])}

@mcp.tool()
def update_pantry_items(user_id: str, items: list = []) -> dict:
    save_pantry(user_id, items)
    return {"user_id": user_id, "items": items, "count": len(items)}


@mcp.tool()
def save_meal_plan_tool(user_id: str, weekly_meals: dict, shopping_list: list,
                        budget_summary: dict = {}, nutrition_report: dict = {}) -> dict:
    return save_meal_plan(user_id, weekly_meals, shopping_list,
                          budget_summary, nutrition_report)

@mcp.tool()
def get_recipe_cache(user_id: str, meal: str) -> dict:
    return get_cached_recipe(user_id, meal)

@mcp.tool()
def save_recipe_cache_tool(user_id: str, meal: str, ingredients: list, source: str = "vertex_ai") -> dict:
    return save_recipe_cache(user_id, meal, ingredients, source)

app = mcp.streamable_http_app()
