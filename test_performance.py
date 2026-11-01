"""Synthetic tables below are test fixtures, not aircraft performance data."""

import json
import unittest
from copy import deepcopy

from app import app
from aircraft import blank_profile, starter_profile
from performance import (COLUMNS, builtin_dataset, empty_dataset, import_rows,
                         manual_cruise, manual_distance, validate_dataset)


def distance_table(phase="takeoff"):
    result = empty_dataset("manual")
    result.update(source="SYNTHETIC TEST TABLE", conditions="Test fixture only",
                  headwind_pct=10, headwind_step_kt=9, headwind_max_kt=18,
                  tailwind_pct=10, tailwind_step_kt=2, tailwind_max_kt=4,
                  grass_mode="ground_add", grass_pct=15)
    for weight in (1000, 1200):
        for pa in (0, 1000):
            for oat in (0, 10):
                ground = 100 + .2 * weight + .01 * pa + 2 * oat
                row = dict(weight_lb=weight, pa_ft=pa, oat_c=oat,
                           ground_ft=ground, total_ft=2 * ground + 50,
                           at_50ft_kias=50)
                if phase == "takeoff":
                    row["lift_off_kias"] = 40
                result["rows"].append(row)
    return result


def cruise_table():
    result = empty_dataset("manual")
    result.update(source="SYNTHETIC CRUISE TABLE", conditions="Test fixture only", reference_weight_lb=1200)
    for pa in (2000, 4000):
        for temp in (0, 10):
            for rpm in (2000, 2200):
                result["rows"].append(dict(pa_ft=pa, isa_offset_c=temp, rpm=rpm,
                    percent_bhp=40 + (rpm - 2000) / 20 - temp * .1,
                    ktas=100 + pa / 1000 + temp / 10 + (rpm - 2000) / 100,
                    gph=5 + (rpm - 2000) / 1000 + temp / 100))
    return result


def wind(headwind=0, tailwind=0):
    return dict(headwind_kt=headwind, tailwind_kt=tailwind, crosswind_kt=None, steps=[])


class ManualPerformanceTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def profile(self):
        profile = blank_profile("c152")
        profile.update(name="Test fixture", registration="C-TEST")
        profile["performance"].update(takeoff=distance_table(), landing=distance_table("landing"), cruise=cruise_table())
        return profile

    def post(self, phase, profile=None, **data):
        return self.client.post("/api/" + phase, data=dict(aircraft_profile=json.dumps(profile or self.profile()), **data))

    def test_takeoff_bilinear_interpolation_and_next_weight_table(self):
        result = manual_distance(distance_table(), "takeoff", 1100, 500, 5, wind(), False)
        self.assertEqual(result["selected_table_lbs"], 1200)
        self.assertAlmostEqual(result["ground_roll_ft"], 355)
        self.assertAlmostEqual(result["total_clear_50ft_ft"], 760)
        self.assertEqual(len([s for s in result["calculation_steps"] if s.get("kind") == "interpolation"]), 2)

    def test_exact_axis_and_single_cell_avoid_zero_denominators(self):
        table = distance_table()
        self.assertEqual(manual_distance(table, "takeoff", 1200, 0, 0, wind(), False)["ground_roll_ft"], 340)
        table["rows"] = [table["rows"][0]]
        self.assertFalse(validate_dataset(table, "takeoff", "c152")[1])
        self.assertEqual(manual_distance(table, "takeoff", 1000, 0, 0, wind(), False)["ground_roll_ft"], 300)

    def test_wind_and_ground_add_grass_use_configured_rules(self):
        result = manual_distance(distance_table(), "takeoff", 1100, 500, 5, wind(headwind=9), True)
        self.assertAlmostEqual(result["ground_roll_ft"], 355 * .9 * 1.15)
        self.assertAlmostEqual(result["total_clear_50ft_ft"], 760 * .9 + 355 * .9 * .15)

    def test_alternative_grass_rule_increases_each_distance(self):
        table = distance_table()
        table["grass_mode"] = "both_percent"
        result = manual_distance(table, "takeoff", 1100, 500, 5, wind(), True)
        self.assertAlmostEqual(result["total_clear_50ft_ft"], 760 * 1.15)

    def test_tailwind_factor_and_limit(self):
        result = manual_distance(distance_table(), "takeoff", 1100, 500, 5, wind(tailwind=2), False)
        self.assertAlmostEqual(result["ground_roll_ft"], 355 * 1.1)
        with self.assertRaisesRegex(ValueError, "exceeds"):
            manual_distance(distance_table(), "takeoff", 1100, 500, 5, wind(tailwind=5), False)

    def test_missing_wind_or_grass_rule_is_not_assumed(self):
        table = distance_table()
        table.update(headwind_pct=None, headwind_step_kt=None, headwind_max_kt=None, grass_mode="none")
        self.assertFalse(validate_dataset(table, "takeoff", "c152")[1])
        with self.assertRaisesRegex(ValueError, "No headwind"):
            manual_distance(table, "takeoff", 1100, 500, 5, wind(headwind=1), False)
        with self.assertRaisesRegex(ValueError, "No grass"):
            manual_distance(table, "takeoff", 1100, 500, 5, wind(), True)

    def test_wind_maximum_is_optional_but_enforced_when_recorded(self):
        table = distance_table()
        table["headwind_max_kt"] = None
        self.assertFalse(validate_dataset(table, "takeoff", "c152")[1])
        result = manual_distance(table, "takeoff", 1100, 500, 5, wind(headwind=9), False)
        self.assertAlmostEqual(result["ground_roll_ft"], 319.5)
        table["headwind_max_kt"] = 8
        with self.assertRaisesRegex(ValueError, "exceeds"):
            manual_distance(table, "takeoff", 1100, 500, 5, wind(headwind=9), False)

    def test_no_extrapolation_for_distance_inputs(self):
        for weight, pa, temp in ((1201, 0, 0), (0, 0, 0), (1000, 1001, 0), (1000, 0, -1), (1000, "nan", 0)):
            with self.subTest(weight=weight, pa=pa, temp=temp), self.assertRaises(ValueError):
                manual_distance(distance_table(), "takeoff", weight, pa, temp, wind(), False)

    def test_landing_uses_its_own_table_and_weight(self):
        result = manual_distance(distance_table("landing"), "landing", 1100, 500, 5, wind(), False)
        self.assertEqual(result["ground_roll_ft"], 355)
        self.assertEqual(result["total_to_clear_50ft_ft"], 760)

    def test_cruise_rpm_temperature_and_altitude_interpolation(self):
        result = manual_cruise(cruise_table(), 3000, 2000, 14, 4000, 14, 2100)
        self.assertAlmostEqual(result["KTAS"], 104.5)
        self.assertAlmostEqual(result["Percent BHP"], 44.5)
        self.assertAlmostEqual(result["GPH"], 5.15)
        self.assertEqual(result["Temp offset from ISA C"], 5)
        self.assertTrue(any("RPM ratio" in step["value"] for step in result["calculation_steps"]))

    def test_cruise_exact_cells_and_reversed_oat_bracket(self):
        result = manual_cruise(cruise_table(), 2000, 4000, 11, 1000, 11, 2000)
        self.assertEqual(result["KTAS"], 102)
        self.assertTrue(any("exact RPM" in step["value"] for step in result["calculation_steps"]))

    def test_cruise_outside_rpm_altitude_temperature_and_oat_ranges(self):
        for args in ((3000, 2000, 14, 4000, 14, 2300), (5000, 2000, 9, 6000, 9, 2100),
                     (3000, 2000, 40, 4000, 40, 2100), (3000, 2000, 14, 2000, 14, 2100)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                manual_cruise(cruise_table(), *args)

    def test_duplicate_and_nonphysical_rows_are_rejected(self):
        table = distance_table()
        for change in (lambda t: t["rows"].append(deepcopy(t["rows"][0])),
                       lambda t: t["rows"][0].update(ground_ft=99999),
                       lambda t: t["rows"][0].update(total_ft="nan")):
            trial = deepcopy(table)
            change(trial)
            with self.assertRaises(ValueError):
                validate_dataset(trial, "takeoff", "c152")

    def test_missing_grid_cells_are_draft_and_never_fall_back(self):
        profile = self.profile()
        profile["performance"]["takeoff"]["rows"].pop()
        response = self.client.post("/api/aircraft/validate", json=profile)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json["result"]["performance_status"]["takeoff"]["ready"])
        self.assertEqual(self.post("takeoff", profile, weight_lbs=1100, pressure_altitude_ft=500, oat_c=5).status_code, 400)

    def test_incomplete_manual_table_can_be_saved_without_blocking_wb(self):
        profile = starter_profile()
        profile["performance"]["takeoff"] = empty_dataset("manual")
        profile["performance"]["takeoff"]["rows"] = [{key: None for key in COLUMNS["takeoff"]}]
        response = self.client.post("/api/aircraft/validate", json=profile)
        self.assertTrue(response.json["result"]["ready"])
        self.assertFalse(response.json["result"]["performance_status"]["takeoff"]["ready"])
        self.assertEqual(self.post("takeoff", profile, weight_lbs=2300, pressure_altitude_ft=0, oat_c=0).status_code, 400)

    def test_all_manual_routes_work_independently_of_missing_wb(self):
        for phase in ("takeoff", "landing"):
            response = self.post(phase, weight_lbs=1100, pressure_altitude_ft=500, oat_c=5)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json["result"]["ground_roll_ft"], 355)
        response = self.post("cruise", pressure_altitude_ft=3000, lower_oat_altitude_ft=2000,
                             lower_oat_c=14, upper_oat_altitude_ft=4000, upper_oat_c=14, rpm=2100)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["result"]["KTAS"], 104.5)

    def test_modes_do_not_allow_wrong_builtin_or_silent_fallback(self):
        for model_id, mode in (("c152", "builtin"), ("c172n", "none")):
            profile = blank_profile(model_id)
            profile["performance"]["takeoff"]["mode"] = mode
            self.assertEqual(self.post("takeoff", profile, weight_lbs=1100, pressure_altitude_ft=500, oat_c=5).status_code, 400)

    def test_import_csv_and_excel_tsv_using_standard_parser(self):
        fields = COLUMNS["takeoff"]
        values = distance_table()["rows"][0]
        for delimiter in (",", "\t"):
            text = "\ufeff" + delimiter.join(fields) + "\r\n" + delimiter.join(str(values[key]) for key in fields)
            self.assertEqual(import_rows("takeoff", text)[0], values)

    def test_invalid_import_leaves_a_clear_error(self):
        for text in ("", "weight,PA,OAT\n1,2,3", ",".join(COLUMNS["takeoff"]) + "\n1000,0,nan,100,200,40,50"):
            response = self.client.post("/api/performance/import", json={"phase": "takeoff", "text": text})
            self.assertEqual(response.status_code, 400)
            self.assertFalse(response.json["ok"])

    def test_builtin_cruise_copy_uses_correct_coordinate_order(self):
        table = builtin_dataset("cruise")
        row = next(r for r in table["rows"] if r["pa_ft"] == 2000 and r["isa_offset_c"] == 0 and r["rpm"] == 2400)
        self.assertEqual((row["percent_bhp"], row["ktas"], row["gph"]), (67, 111, 7.5))
        self.assertFalse(validate_dataset(table, "cruise", "c172n")[1])

    def test_copied_builtin_distance_tables_reproduce_existing_results(self):
        for phase in ("takeoff", "landing"):
            table = builtin_dataset(phase)
            self.assertFalse(validate_dataset(table, phase, "c172n")[1])
            original = self.client.post("/api/" + phase, data=dict(weight_lbs=2300, pressure_altitude_ft=2500, oat_c=25)).json["result"]
            copied = manual_distance(table, phase, 2300, 2500, 25, wind(), False)
            self.assertAlmostEqual(copied["ground_roll_ft"], original["ground_roll_ft"], places=1)
            total_key = "total_clear_50ft_ft" if phase == "takeoff" else "total_to_clear_50ft_ft"
            self.assertAlmostEqual(copied[total_key], original[total_key], places=1)

    def test_manual_route_uses_true_to_magnetic_conversion_before_wind_correction(self):
        response = self.post("takeoff", weight_lbs=1100, pressure_altitude_ft=500, oat_c=5,
                             runway_heading_deg=23, wind_direction_deg=245, wind_speed_kt=9,
                             wind_reference="true", magnetic_variation_deg=15, variation_direction="east")
        self.assertEqual(response.status_code, 200)
        self.assertAlmostEqual(response.json["result"]["ground_roll_ft"], 319.5)
        self.assertTrue(any(step["title"] == "True to magnetic wind direction" for step in response.json["steps"]))

    def test_builtin_data_is_not_modified_by_another_profiles_table(self):
        before = self.client.post("/api/takeoff", data=dict(weight_lbs=2300, pressure_altitude_ft=2000, oat_c=20)).json
        self.post("takeoff", weight_lbs=1100, pressure_altitude_ft=500, oat_c=5)
        after = self.client.post("/api/takeoff", data=dict(weight_lbs=2300, pressure_altitude_ft=2000, oat_c=20)).json
        self.assertEqual(after, before)

    def test_profile_backup_roundtrip_preserves_all_performance_cells(self):
        profile = self.profile()
        first = self.client.post("/api/aircraft/validate", json=profile).json["result"]
        restored = self.client.post("/api/aircraft/validate", json=json.loads(json.dumps(first["profile"]))).json["result"]
        self.assertEqual(first["profile"]["performance"], restored["profile"]["performance"])
        self.assertTrue(all(status["ready"] for status in restored["performance_status"].values()))


if __name__ == "__main__":
    unittest.main()
