import unittest
from unittest.mock import patch

from backend.agent import chat_tool_router


class ChatToolRouterTests(unittest.TestCase):
    def test_tool_triggering_message_returns_steps_cards_and_context(self):
        pantry_result = {
            "name": "get_pantry_items",
            "status": "success",
            "summary": "Found 2 pantry item(s).",
            "data": {"user_id": "user-1", "items": ["rice", "beans"], "count": 2},
        }
        recipe_result = {
            "name": "list_recipes",
            "status": "success",
            "summary": "Found 1 saved recipe(s).",
            "data": {"user_id": "user-1", "recipes": [{"meal": "bean bowl"}], "count": 1},
        }
        store_result = {
            "name": "compare_stores",
            "status": "success",
            "summary": "Compared 1 store(s) for 3 item(s).",
            "data": {
                "stores": [{"store_name": "Aldi", "basket_price": 6.5}],
                "shopping_list": ["rice"],
                "count": 1,
            },
        }

        with patch.object(chat_tool_router.tool_wrappers, "get_pantry_items", return_value=pantry_result), \
             patch.object(chat_tool_router.tool_wrappers, "list_recipes", return_value=recipe_result), \
             patch.object(chat_tool_router.tool_wrappers, "compare_stores", return_value=store_result):
            results = chat_tool_router.route_chat_tools(
                "Can I cook a meal from my saved recipes, and where to buy rice on a budget?",
                "user-1",
            )

        steps = chat_tool_router.build_steps(results)
        cards = chat_tool_router.build_cards(results)
        context = chat_tool_router.build_tool_context(results)

        self.assertEqual([step["tool"] for step in steps], [
            "get_pantry_items",
            "list_recipes",
            "compare_stores",
        ])
        self.assertEqual(cards["shopping_list"], ["rice", "beans"])
        self.assertEqual(cards["recipes"], [{"meal": "bean bowl"}])
        self.assertEqual(cards["stores"], [{"store_name": "Aldi", "basket_price": 6.5}])
        payload = chat_tool_router.build_chat_response_payload(
            response_text="Use rice and beans, then buy rice at Aldi.",
            session_id="session-1",
            tool_results=results,
            usage={"used": 1, "limit": 20},
        )

        self.assertIn("get_pantry_items", context)
        self.assertIn("compare_stores", context)
        self.assertEqual(payload["response"], "Use rice and beans, then buy rice at Aldi.")
        self.assertEqual(payload["session_id"], "session-1")
        self.assertEqual(payload["steps"], steps)
        self.assertEqual(payload["cards"], cards)
        self.assertEqual(payload["usage"], {"used": 1, "limit": 20})

    def test_non_triggering_message_returns_empty_steps_and_cards(self):
        results = chat_tool_router.route_chat_tools("Hello there", "user-1")

        self.assertEqual(results, [])
        self.assertEqual(chat_tool_router.build_steps(results), [])
        self.assertEqual(chat_tool_router.build_cards(results), {
            "shopping_list": [],
            "stores": [],
            "recipes": [],
        })
        payload = chat_tool_router.build_chat_response_payload(
            response_text="Hello!",
            session_id="session-2",
            tool_results=results,
            usage={"used": 1, "limit": 20},
        )

        self.assertEqual(
            chat_tool_router.build_tool_context(results),
            "No backend tools matched this message.",
        )
        self.assertEqual(payload["steps"], [])
        self.assertEqual(payload["cards"], {"shopping_list": [], "stores": [], "recipes": []})


if __name__ == "__main__":
    unittest.main()
