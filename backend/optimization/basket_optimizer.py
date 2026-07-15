def optimize_basket(stores, shopping_list):

    optimized = []

    for item in shopping_list:

        cheapest_store = min(
            stores,
            key=lambda s: s["inventory"][item]["price"]
        )

        optimized.append({
            "item": item,
            "store": cheapest_store["name"]
        })

    return optimized