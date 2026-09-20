import unittest

from app.scenario_validation import validate_scenario


class ScenarioValidationTests(unittest.TestCase):
    def test_ui_theme_fields_have_expected_types(self):
        errors = validate_scenario({"id": "test-1", "name": "試作", "ui": {"accent_color": 1, "background_color": 2}, "places": []})
        self.assertIn("ui.accent_color must be text", errors)
        self.assertIn("ui.background_color must be text", errors)

    def test_narrative_fields_must_be_text_when_present(self):
        errors = validate_scenario({"id": "test-1", "name": "試作", "intro": 1, "places": [{"id": "place-1", "name": "地点", "latitude": 35.0, "longitude": 139.0, "radius_m": 40, "points": 120, "description": 2, "hint": 3, "claim_message": 4}]})
        self.assertIn("intro must be text", errors)
        self.assertIn("place-1: description must be text", errors)
        self.assertIn("place-1: hint must be text", errors)
        self.assertIn("place-1: claim_message must be text", errors)

    def test_valid_scenario_has_no_errors(self):
        errors = validate_scenario({"id": "test-1", "name": "試作", "places": [{"id": "place-1", "name": "地点", "latitude": 35.0, "longitude": 139.0, "radius_m": 40, "points": 120}]})
        self.assertEqual([], errors)

    def test_game_duration_and_home_candidates_are_valid_scenario_settings(self):
        errors = validate_scenario({
            "id": "territory-1",
            "name": "陣地戦",
            "game_duration_seconds": 1800,
            "home_candidates": ["high-point-1", "high-point-2"],
            "places": [],
        })
        self.assertEqual([], errors)

    def test_invalid_game_duration_and_home_candidates_are_rejected(self):
        errors = validate_scenario({
            "id": "territory-1",
            "name": "陣地戦",
            "game_duration_seconds": 0,
            "home_candidates": ["ok", 2],
            "places": [],
        })
        self.assertIn("game_duration_seconds must be a positive integer", errors)
        self.assertIn("home_candidates must be a list of place ids", errors)

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
