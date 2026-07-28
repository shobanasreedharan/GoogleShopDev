import importlib
import sys
import types
import unittest


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

    def get(self):
        return _Snapshot(self._store.get(self._path))

    def set(self, value, merge=False):
        current = self._store.get(self._path, {}) if merge else {}
        self._store[self._path] = {**current, **value}

    def update(self, value):
        self.set(value, merge=True)


class _Collection:
    def __init__(self, store, path=()):
        self._store = store
        self._path = path

    def document(self, name):
        return _Document(self._store, self._path + (name,))


class _Database:
    def __init__(self):
        self._store = {}

    def collection(self, name):
        return _Collection(self._store, (name,))


class PantryRepositoryTests(unittest.TestCase):
    def setUp(self):
        self._modules = dict(sys.modules)
        firestore_client = types.ModuleType("backend.db.firestore_client")
        firestore_client.db = _Database()
        sys.modules.pop("backend.db.pantry_repository", None)
        sys.modules["backend.db.firestore_client"] = firestore_client
        self.repository = importlib.import_module("backend.db.pantry_repository")

    def tearDown(self):
        sys.modules.clear()
        sys.modules.update(self._modules)

    def test_add_items_preserves_qty_and_weight(self):
        result = self.repository.add_items(
            "user-1",
            [
                {"name": "atta", "qty": 2, "weight": "10 lb"},
                "rice",
            ],
        )

        self.assertEqual(result, [
            {"name": "atta", "qty": 2, "weight": "10 lb"},
            {"name": "rice", "qty": "", "weight": ""},
        ])
        self.assertEqual(self.repository.get_pantry("user-1"), result)

    def test_add_items_updates_existing_blank_metadata(self):
        self.repository.save_pantry("user-1", ["atta"])

        result = self.repository.add_items("user-1", [{"name": "atta", "qty": 1, "weight": "5 lb"}])

        self.assertEqual(result, [{"name": "atta", "qty": 1, "weight": "5 lb"}])


if __name__ == "__main__":
    unittest.main()
