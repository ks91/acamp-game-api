import unittest

from app.scenario_validation import validate_scenario


class ScenarioValidationTests(unittest.TestCase):
    def test_valid_scenario_has_no_errors(self):
        errors = validate_scenario({"id": "test-1", "name": "試作", "places": [{"id": "place-1", "name": "地点", "latitude": 35.0, "longitude": 139.0, "radius_m": 40, "points": 120}]})
        self.assertEqual([], errors)

    def test_duplicate_place_id_is_rejected(self):
        errors = validate_scenario({"id": "test-1", "name": "試作", "places": [{"id": "same", "name": "A", "latitude": 35.0, "longitude": 139.0, "radius_m": 40, "points": 120}, {"id": "same", "name": "B", "latitude": 35.0, "longitude": 139.0, "radius_m": 40, "points": 120}]})
        self.assertIn("duplicate place id: same", errors)

    def test_invalid_coordinates_and_nonpositive_values_are_rejected(self):
        errors = validate_scenario({"id": "test-1", "name": "試作", "places": [{"id": "bad", "name": "地点", "latitude": 91, "longitude": 181, "radius_m": 0, "points": -1}]})
        self.assertIn("bad: latitude must be between -90 and 90", errors)
        self.assertIn("bad: longitude must be between -180 and 180", errors)
        self.assertIn("bad: radius_m must be positive", errors)
        self.assertIn("bad: points must be positive", errors)


if __name__ == "__main__":
    unittest.main()
