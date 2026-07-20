import unittest
from unittest.mock import patch

from backend.agent.cart_optimization_agent import build_cart_optimization_plan


class CartOptimizationAgentTests(unittest.TestCase):
    def test_builds_expected_response_and_excludes_pantry_items(self):
        with patch("backend.agent.cart_optimization_agent._get_pantry_items", return_value=["rice", "olive oil"]):
            result = build_cart_optimization_plan(
                user_id="user-1",
                shopping_list=["Rice", "Pine Nuts", "Tomatoes", "Olive Oil"],
                substitutions={"pine nuts": ["walnuts"]},
                budget=0.5,
                summary_generator=lambda prompt: "- Removed pantry items\n- Compared stores",
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["summary"], "- Removed pantry items\n- Compared stores")
        self.assertEqual(result["pantry_removed"], ["rice", "olive oil"])
        self.assertIn("store_plan", result)
        self.assertIn("steps", result)
        self.assertTrue(any(s.get("original") == "pine nuts" for s in result["substitutions_applied"]))
        self.assertGreaterEqual(len(result["steps"]), 3)
        self.assertNotIn("rice", [entry["item"] for entry in result["store_plan"]])
        self.assertNotIn("olive oil", [entry["item"] for entry in result["store_plan"]])
        self.assertIsInstance(result["original_total"], float)
        self.assertIsInstance(result["optimized_total"], float)
        self.assertIsInstance(result["estimated_savings"], float)

    def test_bad_input_raises_instead_of_returning_fake_success(self):
        with self.assertRaises(ValueError):
            build_cart_optimization_plan(
                user_id="user-1",
                shopping_list=[],
                substitutions={},
                budget=0.5,
                summary_generator=lambda prompt: "unused",
            )


if __name__ == "__main__":
    unittest.main()
