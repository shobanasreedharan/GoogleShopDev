from backend.db.pantry_repository import get_pantry as _get_pantry, save_pantry


def register_tools(mcp):

    @mcp.tool()
    def get_pantry_items(user_id: str = "demo_user"):
        items = _get_pantry(user_id)
        return {
            "user_id": user_id,
            "items": items or [],
            "count": len(items or [])
        }

    @mcp.tool()
    def update_pantry_items(user_id: str = "demo_user", items: list | None = None):
        items = items or []
        save_pantry(user_id, items)
        return {
            "user_id": user_id,
            "items": items,
            "count": len(items)
        }

    @mcp.tool()
    def get_pantry(user_id: str = "demo_user"):
        """Legacy alias for older registry-style callers."""
        return get_pantry_items(user_id)
