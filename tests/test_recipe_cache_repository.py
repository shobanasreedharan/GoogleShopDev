import importlib
import sys
import types
import unittest
from unittest.mock import patch


class _Snapshot:
    def __init__(self, value):
        self._value = value
        self.exists = value is not None

    def to_dict(self):
        return dict(self._value) if self._value else None


class _Document:
    def __init__(self, store, path):
        self._store = store
        self._path = path

    def collection(self, name):
        return _Collection(self._store, self._path + (name,))

    def get(self):
        return _Snapshot(self._store.get(self._path))

    def set(self, value, merge=False):
        current = self._store.get(self._path, {}) if merge else {}
        self._store[self._path] = {**current, **value}


class _Collection:
    def __init__(self, store, path=()):
        self._store = store
        self._path = path

    def document(self, name):
        return _Document(self._store, self._path + (name,))

    def collection(self, name):
        return _Collection(self._store, self._path + (name,))


class _Database(_Collection):
    def __init__(self):
        self._store = {}
        super().__init__(self._store)


class RecipeCacheRepositoryTests(unittest.TestCase):
    def setUp(self):
        self._modules = dict(sys.modules)
        firestore_client = types.ModuleType("backend.db.firestore_client")
        firestore_client.db = _Database()
        sys.modules.pop("backend.db.recipe_cache_repository", None)
        sys.modules["backend.db.firestore_client"] = firestore_client
        self.repository = importlib.import_module("backend.db.recipe_cache_repository")

    def tearDown(self):
        sys.modules.clear()
        sys.modules.update(self._modules)

    def test_cache_key_normalizes_meal_and_dietary_whitespace(self):
        self.assertEqual(
            self.repository.build_recipe_cache_key("  Lemon   Pasta ", " Vegetarian   Only "),
            "lemon pasta|vegetarian only",
        )

    def test_substitution_update_preserves_cached_instructions(self):
        key = self.repository.build_recipe_cache_key("Lemon Pasta", "None")
        self.repository.save_recipe_cache(
            user_id="user-1",
            meal=key,
            ingredients=["pasta", "lemon"],
            source="gpt-5.6",
            nutrition={"calories": 400},
            substitutions={"pasta": ["rice noodles"]},
            instructions=["Boil pasta"],
        )

        self.repository.save_recipe_cache(
            user_id="user-1",
            meal=key,
            ingredients=["rice noodles", "lemon"],
            source="user_personalized",
            nutrition={"calories": 400},
            substitutions={"pasta": "rice noodles"},
        )

        cached = self.repository.get_cached_recipe("user-1", key)
        self.assertEqual(cached["ingredients"], ["rice noodles", "lemon"])
        self.assertEqual(cached["instructions"], ["Boil pasta"])

    def test_substitution_update_creates_a_missing_cache_entry(self):
        result = self.repository.save_recipe_cache(
            user_id="user-1",
            meal="new meal|none",
            ingredients=["rice noodles"],
            source="user_personalized",
            nutrition={},
            substitutions={"pasta": "rice noodles"},
        )

        self.assertTrue(result["success"])
        cached = self.repository.get_cached_recipe("user-1", "new meal|none")
        self.assertEqual(cached["ingredients"], ["rice noodles"])
        self.assertEqual(cached["instructions"], [])

    def test_single_meal_uses_cached_ingredients_when_substitutions_are_empty(self):
        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = lambda: None
        cached_recipe = {
            "ingredients": ["pasta", "lemon"],
            "substitutions": {},
            "nutrition_report": {},
            "instructions": ["Boil pasta"],
        }
        recipe_module = types.ModuleType("backend.db.recipe_cache_repository")
        recipe_module.build_recipe_cache_key = lambda meal, dietary: f"{meal.lower()}|{dietary.lower()}"
        recipe_module.get_cached_recipe = lambda user_id, key: cached_recipe
        recipe_module.save_recipe_cache = lambda **kwargs: {"success": True}

        sys.modules.pop("backend.agent.unified_ai_agent", None)
        sys.modules["dotenv"] = dotenv
        sys.modules["backend.db.recipe_cache_repository"] = recipe_module
        agent = importlib.import_module("backend.agent.unified_ai_agent")

        with patch.object(agent, "generate_primary_or_fallback") as generate:
            result = agent.run_unified_ai("user-1", {"meal_1": "Lemon Pasta"}, dietary="None")

        generate.assert_not_called()
        self.assertEqual(result["shopping_list"], ["pasta", "lemon"])
        self.assertEqual(result["_source"], "cache")

    def test_single_meal_generation_failure_uses_meal_name_fallback(self):
        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = lambda: None
        recipe_module = types.ModuleType("backend.db.recipe_cache_repository")
        recipe_module.build_recipe_cache_key = lambda meal, dietary: f"{meal.lower()}|{dietary.lower()}"
        recipe_module.get_cached_recipe = lambda user_id, key: None
        recipe_module.save_recipe_cache = lambda **kwargs: {"success": True}

        sys.modules.pop("backend.agent.unified_ai_agent", None)
        sys.modules["dotenv"] = dotenv
        sys.modules["backend.db.recipe_cache_repository"] = recipe_module
        agent = importlib.import_module("backend.agent.unified_ai_agent")

        with patch.object(agent, "generate_primary_or_fallback", side_effect=RuntimeError("model unavailable")):
            result = agent.run_unified_ai("user-1", {"meal_1": "Tomato Pasta"}, dietary="None")

        self.assertEqual(result["_source"], "fallback")
        self.assertFalse(result["_gemini_called"])
        self.assertIn("pasta", result["shopping_list"])
        self.assertIn("tomato", result["shopping_list"])


if __name__ == "__main__":
    unittest.main()
