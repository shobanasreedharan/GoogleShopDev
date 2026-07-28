import unittest

from backend.utils.sanitizers import clean_shopping_list


class SanitizerTests(unittest.TestCase):
    def test_clean_shopping_list_keeps_ingredient_names_only(self):
        self.assertEqual(
            clean_shopping_list([
                "sambar",
                " coconut chutney",
                "1 teaspoon cumin seeds",
                "small onion",
                "coriander leaves (for garnish)",
            ]),
            ["cumin seeds", "onion", "coriander leaves"],
        )


if __name__ == "__main__":
    unittest.main()
