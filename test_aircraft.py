import json
import unittest
from copy import deepcopy

from app import app
from aircraft import blank_profile, catalogue, profile_weight_balance, starter_profile, validate_profile


def complete_profile(model="c172n"):
    profile = blank_profile(model)
    profile.update(id="test-profile", name="Test aircraft", registration="C-TEST",
                   wb_reference="Test fixture / not flight data")
    profile["wb"].update(empty_weight_lb=1541, empty_moment_lb_in=58866.2,
                         max_ramp_lb=2307, usable_fuel_gal=40)
    return profile


def loads(**changes):
    result = dict(pilot_weight_lbs=180, front_passenger_weight_lbs=205,
                  rear_left_weight_lbs=205, rear_right_weight_lbs=0,
                  baggage1_weight_lbs=0, baggage2_weight_lbs=0,
                  fuel_gal=25, taxi_fuel_gal=1, trip_fuel_gal=12)
    result.update(changes)
    return result


class AircraftTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_catalogue_never_supplies_a_tails_empty_weight(self):
        self.assertEqual(len(catalogue()), 16)
        for entry in catalogue():
            with self.subTest(model=entry["id"]):
                self.assertIsNone(entry["template"]["wb"]["empty_weight_lb"])
                self.assertIsNone(entry["template"]["wb"]["empty_moment_lb_in"])
                self.assertEqual(entry["performance_available"], entry["id"] == "c172n")
                validate_profile(entry["template"])

    def test_user_aircraft_restores_confirmed_gfje_wb_values(self):
        profile, issues = validate_profile(starter_profile())
        self.assertEqual((profile["registration"], profile["model_id"], profile["year"], profile["serial_number"]),
                         ("C-GFJE", "c172n", 1979, "17272818"))
        self.assertFalse(issues)
        self.assertEqual(profile["wb"]["empty_weight_lb"], 1541)
        self.assertAlmostEqual(profile["wb"]["empty_moment_lb_in"], 1541 * 38.2)
        self.assertTrue(profile["wb"]["stations"][5]["enabled"])
        self.assertEqual(profile["wb"]["stations"][5]["arm_in"], 123)

    def test_edited_empty_weight_and_baggage_arm_affect_results(self):
        profile = starter_profile()
        profile["wb"].update(empty_weight_lb=1600, empty_moment_lb_in=1600 * 39)
        profile["wb"]["stations"][5]["arm_in"] = 125
        result = profile_weight_balance(profile, loads(baggage2_weight_lbs=10))
        empty = result["rows"][0]
        baggage = next(row for row in result["rows"] if row["item"] == "Baggage 2")
        self.assertEqual((empty["weight"], empty["arm"], empty["moment"]), (1600, 39, 62400))
        self.assertEqual(baggage["moment"], 1250)
        self.assertEqual(result["summary"]["takeoff_weight_lbs"], 2344)

    def test_year_mismatch_is_not_ready(self):
        profile = complete_profile()
        profile["year"] = 1971
        _, issues = validate_profile(profile)
        self.assertTrue(any("Model year mismatch" in issue for issue in issues))

    def test_sample_matches_original_weights_and_preserves_empty_moment(self):
        result = profile_weight_balance(complete_profile(), loads())
        self.assertEqual(result["summary"]["takeoff_weight_lbs"], 2275)
        self.assertEqual(result["summary"]["landing_weight_lbs"], 2203)
        self.assertAlmostEqual(result["rows"][0]["moment"], 58866.2)
        self.assertAlmostEqual(result["summary"]["landing_cg_in"], 92687.2 / 2203)
        self.assertTrue(all(row["status"] == "OK" for row in result["envelope"]))

    def test_station_precision_is_not_rounded_before_totals(self):
        profile = complete_profile()
        profile["wb"]["stations"][0]["arm_in"] = 40.1234
        result = profile_weight_balance(profile, loads(pilot_weight_lbs=180.123))
        pilot = next(row for row in result["rows"] if row["item"] == "Pilot")
        self.assertAlmostEqual(pilot["moment"], 180.123 * 40.1234)

    def test_other_model_uses_its_own_arms_and_envelope(self):
        profile = complete_profile("c172s")
        profile["wb"]["max_ramp_lb"] = 2558
        profile["wb"]["stations"][0]["arm_in"] = 44
        result = profile_weight_balance(profile, loads())
        pilot = next(row for row in result["rows"] if row["item"] == "Pilot")
        self.assertEqual(pilot["moment"], 180 * 44)
        self.assertEqual(result["envelope"][2]["max_weight"], 2550)
        self.assertAlmostEqual(result["envelope"][2]["forward_limit"], 38.25)

    def test_fuel_burn_cannot_exceed_onboard(self):
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            profile_weight_balance(complete_profile(), loads(trip_fuel_gal=25))

    def test_disabled_station_does_not_silently_accept_a_load(self):
        with self.assertRaisesRegex(ValueError, "not enabled"):
            profile_weight_balance(complete_profile(), loads(baggage2_weight_lbs=1))

    def test_baggage_and_fuel_capacity_limits_mark_failure(self):
        result = profile_weight_balance(complete_profile(), loads(baggage1_weight_lbs=121, fuel_gal=41))
        self.assertTrue(all(row["status"] == "FAIL" for row in result["envelope"]))
        self.assertIn("BAGGAGE", result["envelope"][0]["message"])
        self.assertIn("FUEL", result["envelope"][0]["message"])

    def test_taxi_subtracts_weight_and_moment_but_keeps_positive_arm(self):
        result = profile_weight_balance(complete_profile(), loads())
        row = next(row for row in result["rows"] if row["item"] == "Taxi Fuel")
        self.assertEqual((row["arm"], row["weight"], row["moment"]), (48, -6, -288))

    def test_incomplete_and_nonfinite_profiles_cannot_calculate(self):
        response = self.client.post("/api/weight-balance", data=dict(aircraft_profile=json.dumps(blank_profile("c172n")), **loads()))
        self.assertEqual(response.status_code, 400)
        for value in ("nan", "inf", -1, 0):
            with self.subTest(value=value):
                profile = complete_profile()
                profile["wb"]["empty_weight_lb"] = value
                response = self.client.post("/api/aircraft/validate", json=profile)
                self.assertEqual(response.status_code, 400)

    def test_invalid_cg_envelope_is_rejected(self):
        for rows in ([dict(weight_lb=0, forward_in=50, aft_in=40)],
                     [dict(weight_lb=100, forward_in=35, aft_in=47), dict(weight_lb=100, forward_in=35, aft_in=47)]):
            profile = complete_profile()
            profile["wb"]["cg_limits"] = rows
            self.assertEqual(self.client.post("/api/aircraft/validate", json=profile).status_code, 400)

    def test_missing_envelope_points_never_get_172n_defaults(self):
        profile = complete_profile()
        profile["wb"]["cg_limits"] = []
        response = self.client.post("/api/aircraft/validate", json=profile)
        self.assertFalse(response.json["result"]["ready"])

    def test_performance_apis_reject_other_models_and_bad_years(self):
        for model, year in (("c172l", 1971), ("c172s", None), ("c172n", 1971)):
            profile = complete_profile(model)
            profile["year"] = year
            for endpoint in ("takeoff", "landing", "cruise", "climb"):
                with self.subTest(model=model, endpoint=endpoint):
                    response = self.client.post("/api/" + endpoint, data=dict(aircraft_profile=json.dumps(profile)))
                    self.assertEqual(response.status_code, 400)
                    self.assertFalse(response.json["ok"])

    def test_api_uses_profile_not_legacy_empty_aircraft_fields(self):
        profile = complete_profile()
        response = self.client.post("/api/weight-balance", data=dict(
            aircraft_profile=json.dumps(profile), empty_weight_lbs=9999, **loads()))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["result"]["summary"]["takeoff_weight_lbs"], 2275)
        self.assertEqual(response.json["result"]["registration"], "C-TEST")

    def test_backups_can_roundtrip_profile_validation(self):
        profile, issues = validate_profile(complete_profile())
        self.assertFalse(issues)
        restored, restored_issues = validate_profile(json.loads(json.dumps(profile)))
        self.assertEqual(restored, profile)
        self.assertFalse(restored_issues)


if __name__ == "__main__":
    unittest.main()
