import unittest

from app import app, wind_values_from_form


class WindReferenceTests(unittest.TestCase):
    def wind(self, **changes):
        data = dict(runway_heading_deg=23, wind_direction_deg=245,
                    wind_speed_kt=10, wind_reference="true",
                    magnetic_variation_deg=15, variation_direction="east")
        data.update(changes)
        with app.test_request_context(data=data):
            return wind_values_from_form()

    def test_east_variation_aligns_true_wind_with_magnetic_runway(self):
        result = self.wind()
        self.assertAlmostEqual(result["headwind_kt"], 10)
        self.assertAlmostEqual(result["crosswind_kt"], 0)
        self.assertIn("230.0 M", result["steps"][1]["value"])

    def test_west_variation_adds(self):
        result = self.wind(wind_direction_deg=215, variation_direction="west")
        self.assertAlmostEqual(result["headwind_kt"], 10)
        self.assertAlmostEqual(result["crosswind_kt"], 0)

    def test_conversion_wraps_through_north(self):
        for direction, variation_direction, runway in [(5, "east", 35), (355, "west", 1)]:
            with self.subTest(direction=direction):
                result = self.wind(wind_direction_deg=direction,
                                   variation_direction=variation_direction,
                                   runway_heading_deg=runway)
                self.assertAlmostEqual(result["headwind_kt"], 10)
                self.assertAlmostEqual(result["crosswind_kt"], 0)

    def test_magnetic_wind_does_not_apply_variation(self):
        result = self.wind(wind_reference="magnetic", wind_direction_deg=230)
        self.assertAlmostEqual(result["headwind_kt"], 10)

    def test_tailwind_and_crosswind_after_conversion(self):
        self.assertAlmostEqual(self.wind(wind_direction_deg=65)["tailwind_kt"], 10)
        self.assertAlmostEqual(self.wind(wind_direction_deg=335)["crosswind_kt"], 10)

    def test_both_endpoints_return_json_for_missing_variation(self):
        client = app.test_client()
        for endpoint in ("/api/takeoff", "/api/landing"):
            with self.subTest(endpoint=endpoint):
                response = client.post(endpoint, data=dict(
                    runway_heading_deg=23, wind_direction_deg=245,
                    wind_speed_kt=10, wind_reference="true"))
                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json["ok"])

    def test_invalid_variation_is_rejected(self):
        for value in ("nan", "inf", -1, 181):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.wind(magnetic_variation_deg=value)


if __name__ == "__main__":
    unittest.main()
