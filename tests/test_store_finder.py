import sys
import types
import unittest
from unittest.mock import patch

requests = types.ModuleType("requests")
requests.get = lambda *args, **kwargs: None
sys.modules.setdefault("requests", requests)
dotenv = types.ModuleType("dotenv")
dotenv.load_dotenv = lambda: None
sys.modules.setdefault("dotenv", dotenv)

from backend.services import store_finder


class StoreFinderTests(unittest.TestCase):
    def test_receipt_city_stores_are_used_when_places_returns_none(self):
        repo = types.ModuleType("backend.db.store_prices_repository")
        repo.get_currency_for_country = lambda country: "INR"
        repo.get_stores_in_city = lambda city, state, country="US": [
            {"store_name": "Zepto Market", "city": city, "state": state, "country": country}
        ]
        repo.get_lowest_receipt_price_for_item = lambda item, city, state="", country="US": {
            "price": 62.0,
            "currency": "INR",
            "store_name": "Zepto Market",
            "source": "receipt",
        }

        budget = types.ModuleType("backend.optimization.budget_optimizer")
        budget.get_real_price = lambda item, store_name: 2.0

        with patch.dict(sys.modules, {"backend.db.store_prices_repository": repo, "backend.optimization.budget_optimizer": budget}), patch.object(
            store_finder,
            "find_nearby_grocery_stores",
            return_value=[],
        ):
            results = store_finder.recommend_best_store(
                {"lat": 17.385, "lng": 78.4867, "city": "Hyderabad", "region": "Telangana", "country": "IN"},
                ["beans haricot"],
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["store"]["name"], "Zepto Market")
        self.assertEqual(results[0]["items"][0]["price"], 62.0)
        self.assertEqual(results[0]["items"][0]["currency"], "INR")
        self.assertEqual(results[0]["items"][0]["source"], "receipt")
        self.assertEqual(results[0]["items"][0]["price_store"], "Zepto Market")
        self.assertEqual(results[0]["price_breakdown"]["beans haricot"]["source"], "receipt")


if __name__ == "__main__":
    unittest.main()
