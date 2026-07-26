from backend.db.firestore_client import db


def _user_doc(user_id: str):
    return db.collection("users").document(user_id)


def _item_name(item) -> str:
    if isinstance(item, str):
        return item.strip().lower()
    if isinstance(item, dict):
        return str(item.get("name") or item.get("item") or "").strip().lower()
    return ""


def _item_qty(item):
    if not isinstance(item, dict):
        return ""
    value = item.get("qty", item.get("quantity", ""))
    return "" if value is None else value


def _item_weight(item) -> str:
    if not isinstance(item, dict):
        return ""
    return str(item.get("weight") or item.get("measurement") or "").strip()


def _normalize_pantry_entry(item):
    name = _item_name(item)
    if not name:
        return None
    return {"name": name, "qty": _item_qty(item), "weight": _item_weight(item)}


def _normalize_pantry_list(items: list) -> list:
    normalized = []
    seen = set()
    for item in items or []:
        entry = _normalize_pantry_entry(item)
        if not entry or entry["name"] in seen:
            continue
        normalized.append(entry)
        seen.add(entry["name"])
    return normalized


# -----------------------------------
# CREATE / REPLACE PANTRY
# -----------------------------------

def save_pantry(user_id: str, items: list) -> dict:
    normalized = _normalize_pantry_list(items)
    _user_doc(user_id).set({"pantry_items": normalized}, merge=True)
    print(f"Updated pantry for {user_id}: {len(normalized)} items")
    return {"user_id": user_id, "items": normalized}


# -----------------------------------
# GET PANTRY
# -----------------------------------

def get_pantry(user_id: str) -> list:
    """
    Returns pantry items for user
    """
    doc = _user_doc(user_id).get()

    if not doc.exists:
        return []

    return doc.to_dict().get("pantry_items", [])


# -----------------------------------
# ADD ITEMS
# -----------------------------------

def add_items(user_id: str, new_items: list) -> list:
    """
    Add new pantry items, preserving optional qty/weight metadata.
    """
    merged_by_name = {entry["name"]: entry for entry in _normalize_pantry_list(get_pantry(user_id))}

    for entry in _normalize_pantry_list(new_items):
        existing = merged_by_name.get(entry["name"], {"name": entry["name"], "qty": "", "weight": ""})
        merged_by_name[entry["name"]] = {
            "name": entry["name"],
            "qty": entry.get("qty") if entry.get("qty") not in (None, "") else existing.get("qty", ""),
            "weight": entry.get("weight") or existing.get("weight", ""),
        }

    merged = list(merged_by_name.values())
    save_pantry(user_id, merged)

    return merged


# -----------------------------------
# REMOVE ITEMS
# -----------------------------------

def remove_items(user_id: str, items_to_remove: list) -> dict:
    """
    Remove specific items from pantry
    """
    current = get_pantry(user_id)

    remove_names = {_item_name(item) for item in items_to_remove}
    updated = [
        item
        for item in _normalize_pantry_list(current)
        if item["name"] not in remove_names
    ]

    save_pantry(user_id, updated)

    return {
        "updated": updated,
        "removed": items_to_remove
    }


# -----------------------------------
# CLEAR PANTRY
# -----------------------------------

def clear_pantry(user_id: str):
    _user_doc(user_id).update({"pantry_items": []})


# -----------------------------------
# DEBUG
# -----------------------------------

if __name__ == "__main__":

    TEST_USER = "debug_test_user"

    save_pantry(
        TEST_USER,
        ["rice", "salt", "olive oil"]
    )

    print("Pantry:")
    print(get_pantry(TEST_USER))

    add_items(
        TEST_USER,
        ["garlic", "onion"]
    )

    print("After Add:")
    print(get_pantry(TEST_USER))

    remove_items(
        TEST_USER,
        ["salt"]
    )

    print("After Remove:")
    print(get_pantry(TEST_USER))
