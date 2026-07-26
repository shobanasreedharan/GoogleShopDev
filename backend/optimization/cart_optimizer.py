from backend.services.location import get_user_location
from backend.services.store_finder import haversine_distance
from backend.services.store_finder import mock_check_inventory

def optimize_cart(stores, shopping_list, user_location):

    allocation = {}

    for item in shopping_list:

        ranked_stores = []

        for store in stores:

            inventory = mock_check_inventory(store["name"], [item])

            if not inventory[item]["available"]:
                continue

            price = inventory[item]["price"]

            distance = haversine_distance(
                user_location["lat"],
                user_location["lng"],
                store["lat"],
                store["lng"]
            )

            score = price * 0.7 + distance * 0.3

            ranked_stores.append((score, store["name"]))

        ranked_stores.sort()

        # 🔥 instead of 1 store, keep TOP 2
        allocation[item] = ranked_stores[:2]

    return allocation