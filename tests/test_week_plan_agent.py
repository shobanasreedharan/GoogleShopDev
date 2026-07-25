import importlib
import sys
import types
import unittest


class WeekPlanAgentTests(unittest.TestCase):
    def setUp(self):
        self._modules = dict(sys.modules)

        pantry_repo = types.ModuleType("backend.db.pantry_repository")
        pantry_repo.get_pantry = lambda user_id: ["tomato", "rice"]
        sys.modules["backend.db.pantry_repository"] = pantry_repo

        unified = types.ModuleType("backend.agent.unified_ai_agent")
        unified.generate_text = lambda prompt: '{"meals":[{"name":"Tomato Pasta","reason":"Uses pantry tomato"},{"name":"Rice Bowl","reason":"Uses pantry rice"}]}'
        unified.run_unified_ai = lambda **kwargs: {
            "shopping_list": ["tomato", "pasta", "rice", "beans"],
            "substitutions": {},
            "nutrition_report": {},
            "_gemini_called": False,
            "_source": "test",
        }
        sys.modules["backend.agent.unified_ai_agent"] = unified

        budget = types.ModuleType("backend.optimization.budget_optimizer")
        budget.weekly_budget_planner = lambda items, weekly_budget, recommended_stores=None: {
            "budget": weekly_budget,
            "optimization": {
                "optimized_list": items,
                "original_cost": 20,
                "optimized_cost": 14,
                "money_saved": 6,
                "substitutions": [],
            },
        }
        sys.modules["backend.optimization.budget_optimizer"] = budget

        location = types.ModuleType("backend.services.location")
        location.get_user_location = lambda **kwargs: {
            "lat": 17.385,
            "lng": 78.4867,
            "city": "Hyderabad",
            "region": "Telangana",
            "country": "IN",
        }
        sys.modules["backend.services.location"] = location

        finder = types.ModuleType("backend.services.store_finder")
        finder.recommend_best_store = lambda user_location, shopping_list: [
            {
                "store": {"name": "Zepto Market", "lat": 17.38, "lng": 78.48},
                "score": {"total_price": 14, "distance_km": 1.2, "final_score": 0.9},
                "items": [
                    {"item": "pasta", "price": 8, "currency": "INR", "source": "estimate"},
                    {"item": "beans", "price": 6, "currency": "INR", "source": "receipt"},
                ],
                "price_breakdown": {
                    "pasta": {"price": 8, "currency": "INR", "source": "estimate"},
                    "beans": {"price": 6, "currency": "INR", "source": "receipt"},
                },
            }
        ]
        sys.modules["backend.services.store_finder"] = finder

        sanitizers = types.ModuleType("backend.utils.sanitizers")
        sanitizers.clean_stores = lambda stores: stores
        sys.modules["backend.utils.sanitizers"] = sanitizers

        sys.modules.pop("backend.agent.week_plan_agent", None)
        self.agent = importlib.import_module("backend.agent.week_plan_agent")

    def tearDown(self):
        sys.modules.clear()
        sys.modules.update(self._modules)

    def test_build_week_plan_chains_existing_tools_and_returns_review_shape(self):
        result = self.agent.build_week_plan(
            "user-1",
            budget=50,
            dietary_instruction="Vegetarian",
            manual_city="Hyderabad",
            manual_state="Telangana",
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["requires_approval"])
        self.assertEqual([m["name"] for m in result["suggested_meals"]], ["Tomato Pasta", "Rice Bowl"])
        self.assertEqual(result["pantry_items_used"], ["tomato", "rice"])
        self.assertEqual(result["combined_shopping_list"], ["pasta", "beans"])
        self.assertEqual(result["price_sources"], {"pasta": "estimate", "beans": "receipt"})
        self.assertEqual(result["estimated_savings"], 6.0)
        self.assertGreaterEqual(len(result["steps"]), 4)

    def test_negative_budget_is_bad_input(self):
        with self.assertRaises(ValueError):
            self.agent.build_week_plan("user-1", budget=-1)


if __name__ == "__main__":
    unittest.main()
