from collections import defaultdict


def build_weekly_shopping_list(recipe_results):

    merged = defaultdict(int)

    for recipe in recipe_results:

        for item in recipe["shopping_list"]:
            merged[item.lower()] += 1

    return dict(merged)