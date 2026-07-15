from collections import Counter


def cluster_meals(recipe_data):

    ingredient_counter = Counter()

    for recipe in recipe_data:
        ingredient_counter.update(recipe["shopping_list"])

    repeated_items = {
        item: count
        for item, count in ingredient_counter.items()
        if count > 1
    }

    return repeated_items