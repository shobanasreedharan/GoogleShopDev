import sys
import types
import unittest

from backend.agent import tool_wrappers


class ToolWrapperTests(unittest.TestCase):
    def setUp(self):
        self._saved = dict(sys.modules)

    def tearDown(self):
        sys.modules.clear()
        sys.modules.update(self._saved)

    def _install_module(self, name, **attrs):
        module = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(module, key, value)
        sys.modules[name] = module
        return module

    def test_get_pantry_items_shape(self):
        self._install_module(
            "backend.db.pantry_repository",
            get_pantry=lambda user_id: ["rice", "beans"],
        )

        result = tool_wrappers.get_pantry_items("user-1")

        self.assertEqual(result["name"], "get_pantry_items")
        self.assertEqual(result["status"], "success")
        self.assertIn("2", result["summary"])
        self.assertEqual(result["data"]["items"], ["rice", "beans"])
        self.assertEqual(result["data"]["count"], 2)

    def test_list_recipes_shape(self):
        recipes = [{"meal": "pasta", "ingredients": ["noodles"]}]
        self._install_module(
            "backend.db.recipe_cache_repository",
            list_recipes=lambda user_id: recipes,
        )

        result = tool_wrappers.list_recipes("user-1")

        self.assertEqual(result["name"], "list_recipes")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["recipes"], recipes)
        self.assertEqual(result["data"]["count"], 1)

    def test_compare_stores_shape(self):
        raw_store_results = [{
            "store": {
                "name": "Aldi",
                "brand": "Aldi",
                "address": "1 Main St",
                "lat": 32.1,
                "lng": -96.8,
            },
            "score": {"total_price": 3.5, "distance_km": 1.2, "final_score": 0.9},
            "items": [{"item": "rice", "price": 3.5, "currency": "USD"}],
            "price_breakdown": {"rice": {"price": 3.5, "currency": "USD"}},
            "unavailable_items": [],
        }]
        self._install_module(
            "backend.services.store_finder",
            recommend_best_store=lambda user_location, shopping_list: raw_store_results,
        )
        self._install_module(
            "backend.utils.sanitizers",
            clean_stores=lambda results: results,
        )

        result = tool_wrappers.compare_stores(
            {"lat": 32.0, "lng": -96.0, "city": "Dallas", "region": "TX", "country": "US"},
            [" Rice "],
        )

        self.assertEqual(result["name"], "compare_stores")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["shopping_list"], ["rice"])
        self.assertEqual(result["data"]["stores"][0]["store_name"], "Aldi")
        self.assertEqual(result["data"]["count"], 1)

    def test_error_shape(self):
        result = tool_wrappers.get_pantry_items("")

        self.assertEqual(result["name"], "get_pantry_items")
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["data"])
        self.assertIn("user_id", result["summary"])


if __name__ == "__main__":
    unittest.main()
