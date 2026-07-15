from backend.db.pantry_repository import get_pantry

uid = "YkVasEWUS3N5DoHyAEF6BZ8pPmc2"
items = get_pantry(uid)
print(f"Pantry for {uid}: {items}")
