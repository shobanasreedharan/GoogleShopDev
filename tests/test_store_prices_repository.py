import importlib
import sys
import types
import unittest


class _Snapshot:
    def __init__(self, key, value):
        self.id = key[-1] if key else ""
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
        return _Snapshot(self._path, self._store.get(self._path))

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

    def stream(self):
        depth = len(self._path) + 1
        for path, value in sorted(self._store.items()):
            if len(path) == depth and path[:-1] == self._path:
                yield _Snapshot(path, value)


class _Database(_Collection):
    def __init__(self):
        self._store = {}
        super().__init__(self._store)


class StorePricesRepositoryTests(unittest.TestCase):
    def setUp(self):
        self._modules = dict(sys.modules)
        firestore_client = types.ModuleType("backend.db.firestore_client")
        firestore_client.db = _Database()
        sys.modules.pop("backend.db.store_prices_repository", None)
        sys.modules["backend.db.firestore_client"] = firestore_client
        self.repository = importlib.import_module("backend.db.store_prices_repository")

    def tearDown(self):
        sys.modules.clear()
        sys.modules.update(self._modules)

    def test_receipt_prices_are_written_and_read_by_normalized_city(self):
        result = self.repository.save_store_prices(
            uploaded_by="user-1",
            store_name="Fresh Market",
            city="  St. Louis ",
            state=" MO ",
            country="US",
            items={"Organic Milk": {"price": "4.49", "unit": "each"}},
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["city_key"], "us_mo_st_louis")
        self.assertEqual(result["sample_path"], "city_prices/us_mo_st_louis/items/organic_milk")

        price = self.repository.get_real_price("organic milk", "Fresh Market", "st louis", "mo")
        self.assertEqual(price, {"price": 4.49, "currency": "USD"})

    def test_country_name_india_saves_inr_currency(self):
        result = self.repository.save_store_prices(
            uploaded_by="user-1",
            store_name="Reliance Fresh",
            city="Hyderabad",
            state="Telangana",
            country="India",
            items={"atta": {"price": 249, "currency": "USD"}},
        )

        self.assertEqual(result["city_key"], "in_telangana_hyderabad")
        price = self.repository.get_real_price("atta", "Reliance Fresh", "hyderabad", "telangana", "India")
        self.assertEqual(price, {"price": 249.0, "currency": "INR"})
        self.assertEqual(result["items_preview"]["atta"]["currency"], "INR")

    def test_stores_in_city_uses_city_prices_subcollection(self):
        self.repository.save_store_prices(
            uploaded_by="user-1",
            store_name="Fresh Market",
            city="Austin",
            state="Texas",
            country="US",
            items={"rice": {"price": 2.5}},
        )

        stores = self.repository.get_stores_in_city(" austin ", "texas")
        self.assertEqual(len(stores), 1)
        self.assertEqual(stores[0]["store_name"], "Fresh Market")

    def test_invalid_receipt_items_raise_instead_of_fake_success(self):
        with self.assertRaises(ValueError):
            self.repository.save_store_prices(
                uploaded_by="user-1",
                store_name="Fresh Market",
                city="Austin",
                state="Texas",
                items={},
            )


if __name__ == "__main__":
    unittest.main()
