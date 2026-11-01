import json
import unittest

from app import app
from aircraft import ffct_profile, validate_profile
from reference_1974 import (MPH_PER_KNOT, reference_cruise, reference_distance,
                            table_view)


def wind(headwind=0, tailwind=0):
    return dict(headwind_kt=headwind, tailwind_kt=tailwind, crosswind_kt=None, steps=[])


class Reference1974Tests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_ffct_identity_and_no_gfje_empty_aircraft_data(self):
        profile, issues = validate_profile(ffct_profile())
        self.assertEqual((profile["registration"], profile["model_id"], profile["year"], profile["serial_number"]),
                         ("C-FFCT", "c172m", 1974, "17262961"))
        self.assertIsNone(profile["wb"]["empty_weight_lb"])
        self.assertIsNone(profile["wb"]["empty_moment_lb_in"])
        self.assertTrue(issues)
        self.assertTrue(all(data["mode"] == "c172m1974" for data in profile["performance"].values()))

    def test_published_reference_spot_values(self):
        result = reference_distance("takeoff", 2300, 0, 15, wind(headwind=10), False)
        self.assertEqual(result["ground_roll_ft"], 615)
        self.assertEqual(result["total_clear_50ft_ft"], 1170)
        result = reference_distance("takeoff", 1700, 0, 15, wind(headwind=20), False)
        self.assertEqual(result["total_clear_50ft_ft"], 385)

    def test_takeoff_altitude_and_headwind_then_temperature_then_grass(self):
        result = reference_distance("takeoff", 2250, 3750, 20, wind(headwind=5), True)
        # Four original cells: GR 1040/750/1255/920; total 1910/1485/2480/1955.
        ground = 991.25 * 1.09
        total = 1957.5 * 1.09
        self.assertAlmostEqual(result["ground_roll_ft"], ground + .07 * total)
        self.assertAlmostEqual(result["total_clear_50ft_ft"], total * 1.07)
        self.assertEqual(result["selected_table_lbs"], 2300)
        self.assertEqual(next(s for s in result["calculation_steps"] if s.get("kind") == "interpolation")["axis_label"], "PA / Headwind")

    def test_cold_temperature_does_not_get_an_invented_reduction(self):
        result = reference_distance("takeoff", 2300, 0, -10, wind(), False)
        self.assertEqual(result["ground_roll_ft"], 865)
        self.assertEqual(result["total_clear_50ft_ft"], 1525)

    def test_landing_1974_headwind_and_total_based_grass(self):
        result = reference_distance("landing", 2200, 3750, 7.5, wind(headwind=5), True)
        self.assertAlmostEqual(result["ground_roll_ft"], 582.5 * .9 + 1347.5 * .9 * .2)
        self.assertAlmostEqual(result["total_to_clear_50ft_ft"], 1347.5 * .9 * 1.2)
        self.assertAlmostEqual(result["approach_kias"], 70 / MPH_PER_KNOT)
        self.assertNotIn("at_50ft_kias", result)

    def test_source_does_not_supply_nonstandard_landing_or_tailwind_correction(self):
        for phase, temp, w in (("landing", 20, wind()), ("landing", 15, wind(tailwind=1)), ("takeoff", 15, wind(tailwind=1))):
            with self.subTest(phase=phase, temp=temp), self.assertRaises(ValueError):
                reference_distance(phase, 2300, 0, temp, w, False)

    def test_outside_table_inputs_are_rejected(self):
        for weight, pa, w in ((2301, 0, wind()), (2300, 7501, wind()), (2300, 0, wind(headwind=21))):
            with self.subTest(weight=weight, pa=pa), self.assertRaises(ValueError):
                reference_distance("takeoff", weight, pa, 15, w, False)

    def test_cruise_exact_cell_converts_original_mph_to_ktas(self):
        result = reference_cruise(5000, 2500, 10, 7500, 0, 2400)
        self.assertEqual(result["Percent BHP"], 60)
        self.assertEqual(result["GPH"], 6.8)
        self.assertAlmostEqual(result["KTAS"], 121 / MPH_PER_KNOT)

    def test_cruise_interpolates_rpm_and_altitude_in_native_units(self):
        result = reference_cruise(6250, 5000, 5, 7500, 0, 2450)
        self.assertAlmostEqual(result["Percent BHP"], 61.5)
        self.assertAlmostEqual(result["GPH"], 6.975)
        self.assertAlmostEqual(result["KTAS"], 123.5 / MPH_PER_KNOT)

    def test_cruise_rejects_nonstandard_temperature_high_power_and_extrapolation(self):
        for values in ((5000, 2500, 20, 7500, 10, 2400), (2500, 0, 15, 5000, 5, 2600), (2000, 0, 15, 5000, 5, 2400), (5000, 2500, 10, 7500, 0, 2100)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                reference_cruise(*values)

    def test_reference_data_is_visible_with_original_units(self):
        self.assertEqual(len(table_view("takeoff")["rows"]), 36)
        self.assertEqual(len(table_view("landing")["rows"]), 4)
        self.assertEqual(len(table_view("cruise")["rows"]), 25)
        self.assertIn("Skyhawk TAS (MPH)", table_view("cruise")["columns"])
        self.assertEqual(self.client.get("/api/performance/reference-1974/invalid").status_code, 400)

    def test_routes_use_reference_data_without_requiring_unknown_empty_weight(self):
        profile = json.dumps(ffct_profile())
        for phase in ("takeoff", "landing"):
            response = self.client.post("/api/" + phase, data=dict(aircraft_profile=profile, weight_lbs=2300, pressure_altitude_ft=0, oat_c=15))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["result"]["ground_roll_ft"], 865 if phase == "takeoff" else 520)
        response = self.client.post("/api/cruise", data=dict(aircraft_profile=profile, pressure_altitude_ft=5000,
            lower_oat_altitude_ft=2500, lower_oat_c=10, upper_oat_altitude_ft=7500, upper_oat_c=0, rpm=2400))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["result"]["GPH"], 6.8)
        self.assertEqual(self.client.post("/api/climb", data=dict(aircraft_profile=profile)).status_code, 400)

    def test_reference_cannot_be_used_as_another_model_or_year(self):
        for model, year in (("c172n", 1979), ("c172m", 1976)):
            profile = ffct_profile()
            profile.update(model_id=model, year=year)
            response = self.client.post("/api/takeoff", data=dict(aircraft_profile=json.dumps(profile), weight_lbs=2300, pressure_altitude_ft=0, oat_c=15))
            self.assertEqual(response.status_code, 400)

    def test_starter_profiles_keep_gfje_and_add_ffct(self):
        data = self.client.get("/api/aircraft/models").json
        self.assertEqual([profile["registration"] for profile in data["starter_profiles"]], ["C-GFJE", "C-FFCT"])
        self.assertEqual(data["starter_profile"]["registration"], "C-GFJE")


if __name__ == "__main__":
    unittest.main()
