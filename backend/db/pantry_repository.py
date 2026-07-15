from backend.db.firestore_client import db


def _user_doc(user_id: str):
    return db.collection("users").document(user_id)


# -----------------------------------
# CREATE / REPLACE PANTRY
# -----------------------------------

def save_pantry(user_id: str, items: list) -> dict:
    _user_doc(user_id).set({"pantry_items": items}, merge=True)
    print(f"Updated pantry for {user_id}: {len(items)} items")
    return {"user_id": user_id, "items": items}


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
    Add new pantry items
    """
    current = get_pantry(user_id)

    merged = list(
        set(
            [x.lower() for x in current]
            +
            [x.lower() for x in new_items]
        )
    )

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

    updated = [
        item
        for item in current
        if item.lower() not in [x.lower() for x in items_to_remove]
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
