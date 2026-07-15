def fallback_ingredients(meals: dict):
    """
    Deterministic fallback when AI fails
    """

    base_map = {
        "pasta": ["pasta", "tomato", "salt", "olive oil"],
        "rice": ["rice", "salt", "oil"],
        "tofu": ["tofu", "soy sauce", "garlic"],
        "curry": ["onion", "tomato", "spices"],
        "stir fry": ["vegetables", "soy sauce", "oil"]
    }

    result = {}

    for day, meal in meals.items():
        meal_lower = meal.lower()

        ingredients = []

        for key, items in base_map.items():
            if key in meal_lower:
                ingredients.extend(items)

        if not ingredients:
            ingredients = ["salt", "oil", "vegetables"]

        result[day] = ingredients

    return result