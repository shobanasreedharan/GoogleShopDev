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
        self.assertEqual(price, {"price": 4.49, "currency": "USD", "measurement": "", "quantity": 1})


    def test_receipt_line_total_is_saved_as_unit_price_with_measurement_only(self):
        result = self.repository.save_store_prices(
            uploaded_by="user-1",
            store_name="Desi Bazar",
            city="Austin",
            state="Texas",
            country="US",
            items={"atta 10 lb": {"quantity": 2, "line_total": 13.98, "unit": "bag"}},
        )

        price = self.repository.get_real_price("atta 10 lb", "Desi Bazar", "Austin", "Texas")
        self.assertEqual(price, {"price": 6.99, "currency": "USD", "measurement": "10 lb", "quantity": 1})
        item_doc = self.repository._city_doc("Austin", "Texas", "US").collection("items").document("atta_10_lb").get().to_dict()
        saved_price = next(iter(item_doc["prices"].values()))
        self.assertEqual(saved_price["price"], 6.99)
        self.assertEqual(saved_price["measurement"], "10 lb")
        self.assertNotIn("line_price", saved_price)
        self.assertNotIn("quantity", saved_price)
        self.assertEqual(result["sample_path"], "city_prices/us_texas_austin/items/atta_10_lb")

    def test_visible_unit_list_price_wins_over_line_total(self):
        self.repository.save_store_prices(
            uploaded_by="user-1",
            store_name="Market",
            city="Austin",
            state="Texas",
            country="US",
            items={"apples": {"quantity": 3, "unit_list_price": 1.25, "line_total": 3.75}},
        )

        price = self.repository.get_real_price("apples", "Market", "Austin", "Texas")
        self.assertEqual(price, {"price": 1.25, "currency": "USD", "measurement": "", "quantity": 1})

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
