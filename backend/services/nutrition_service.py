from data.nutrition_db import NUTRITION_DB


def calculate_nutrition(shopping_list):

    totals = {
        "calories": 0,
        "protein_g": 0,
        "carbs_g": 0,
        "fat_g": 0,
        "fiber_g": 0,
    }

    for item in shopping_list:

        key = item.lower()

        if key not in NUTRITION_DB:
            continue

        nutrient = NUTRITION_DB[key]

        for k in totals:
            totals[k] += nutrient.get(k, 0)

    return totals