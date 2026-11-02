"""Build-time POH data export only. No Python runtime is included in the native app."""
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aircraft import catalogue, starter_profile, ffct_profile
from performance import builtin_dataset
from reference_1974 import table_view, conditions, SOURCE_URL
import climb


def export():
    data = dict(catalogue=catalogue(), profiles=[starter_profile(), ffct_profile()],
                builtin={phase: builtin_dataset(phase) for phase in ("takeoff", "landing", "cruise")},
                reference={phase: table_view(phase) for phase in ("takeoff", "landing", "cruise")},
                climb=[dict(pa_ft=float(altitude), **{key: float(value) for key, value in climb.table_at(altitude).items()}) for altitude in climb.alt])
    data["builtin"]["climb"] = dict(
        mode="manual", source="Existing C172N POH Figure 5-6 table; verify edition and aircraft applicability",
        conditions="Cumulative sea-level time, fuel and distance; use only at the POH weight and configuration. No cold-temperature credit.",
        warm_temp_pct=10.0, warm_temp_step_c=10.0, start_taxi_takeoff_fuel_gal=1.1,
        rows=data["climb"])
    for profile in data["profiles"] + [model["template"] for model in data["catalogue"]]:
        profile["performance"]["climb"] = dict(
            mode="builtin" if profile["model_id"] == "c172n" else "none",
            source="", conditions="", rows=[])
    destination = ROOT / "ios/Resources/NativeData.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, allow_nan=False, separators=(",", ":")), encoding="utf-8")
    from offline_cases import cases
    samples = [sample for sample in cases() if sample["path"] in ("/api/takeoff", "/api/landing", "/api/cruise", "/api/climb", "/api/weight-balance")]
    from app import app
    rng = random.Random(172)
    for phase in ("takeoff", "landing"):
        for index in range(30):
            body = dict(weight_lbs=str(rng.uniform(1700, 2300)), pressure_altitude_ft=str(rng.uniform(0, 8000)),
                        oat_c=str(rng.uniform(0, 40)), runway_heading_deg="23", wind_direction_deg="230",
                        wind_reference="magnetic", wind_speed_kt=str(rng.uniform(0, 18)), grass="on" if index % 2 else "")
            with app.test_client() as client:
                response = client.post("/api/" + phase, data=body)
            samples.append(dict(name=f"{phase} random {index}", path="/api/" + phase, body=body,
                                expected=dict(status=response.status_code, body=response.get_json())))
    def add(name, phase, body):
        with app.test_client() as client:
            response = client.post("/api/" + phase, data=body)
        samples.append(dict(name=name, path="/api/" + phase, body=body,
                            expected=dict(status=response.status_code, body=response.get_json())))
    for index in range(15):
        offset = rng.uniform(-15, 15)
        add(f"cruise random {index}", "cruise", dict(pressure_altitude_ft=str(rng.uniform(2000, 12000)), rpm=str(rng.uniform(2250, 2400)),
            lower_oat_altitude_ft="2000", lower_oat_c=str(11 + offset), upper_oat_altitude_ft="12000", upper_oat_c=str(-9 + offset)))
        add(f"climb random {index}", "climb", dict(pressure_altitude_ft=str(rng.uniform(0, 5999)), target_altitude_ft=str(rng.uniform(6001, 12000)), oat_c=str(rng.uniform(-10, 35))))
        add(f"W&B random {index}", "weight-balance", dict(aircraft_profile=json.dumps(starter_profile()), pilot_weight_lbs=str(rng.uniform(100, 240)),
            front_passenger_weight_lbs=str(rng.uniform(0, 240)), rear_left_weight_lbs=str(rng.uniform(0, 230)), rear_right_weight_lbs=str(rng.uniform(0, 230)),
            baggage1_weight_lbs=str(rng.uniform(0, 60)), baggage2_weight_lbs=str(rng.uniform(0, 40)), fuel_gal="35", taxi_fuel_gal="1", trip_fuel_gal="12"))
    target = ROOT / "ios/Tests/Fixtures/NativeParity.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(samples, allow_nan=False), encoding="utf-8")
    print(f"Native POH data: {destination.stat().st_size} bytes; {len(samples)} parity cases")


if __name__ == "__main__":
    export()
