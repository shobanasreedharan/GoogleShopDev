import unittest

from backend.optimization.route_optimizer import optimize_route


class RouteOptimizerTests(unittest.TestCase):
    def test_ignores_stores_without_coordinates(self):
        route = optimize_route(
            [
                {"name": "Receipt Only Store", "lat": None, "lng": None},
                {"name": "Mapped Store", "lat": 38.63, "lng": -90.2},
            ],
            {"lat": 38.627, "lng": -90.1994},
        )

        self.assertEqual([store["name"] for store in route], ["Mapped Store"])


if __name__ == "__main__":
    unittest.main()
