from backend.db.pantry_repository import get_pantry

def register_tools(mcp):

    @mcp.tool()
    def get_pantry(user_id: str = "demo_user"):
        items = get_pantry(user_id)
        return {
            "user_id": user_id,
            "items": items or [],
            "count": len(items or [])
        }