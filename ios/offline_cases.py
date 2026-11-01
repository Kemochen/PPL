"""Golden API cases produced by the website for the bundled-runtime parity test."""
import json
from app import app
from aircraft import starter_profile, ffct_profile
from performance import builtin_dataset


def cases():
    result = []
    def add(name, path, body=None, as_json=False):
        method = "POST" if body is not None else "GET"
        with app.test_client() as client:
            response = client.open(path, method=method, **({"json": body} if as_json else {"data": body}))
        result.append(dict(name=name, path=path, method=method, body=body, json=as_json,
                           expected=dict(status=response.status_code, body=response.get_json())))
    add("aircraft catalogue", "/api/aircraft/models")
    for phase in ("takeoff", "landing", "cruise"):
        add("builtin " + phase, "/api/performance/builtin/" + phase)
        add("1974 source " + phase, "/api/performance/reference-1974/" + phase)
    inputs = dict(weight_lbs="2300", pressure_altitude_ft="2350", oat_c="23.7",
                  runway_heading_deg="23", wind_direction_deg="245", wind_speed_kt="10",
                  wind_reference="true", magnetic_variation_deg="15", variation_direction="east", grass="on")
    add("takeoff bilinear warm grass wind", "/api/takeoff", inputs)
    add("landing bilinear warm grass wind", "/api/landing", inputs)
    add("missing true wind variation", "/api/takeoff", {**inputs, "magnetic_variation_deg": ""})
    for pa in ("0", "8000", "8001"):
        add("takeoff boundary " + pa, "/api/takeoff", {**inputs, "pressure_altitude_ft": pa})
    add("climb interpolation", "/api/climb", dict(pressure_altitude_ft="500", target_alt_ft="6500", oat_c="25"))
    add("climb out of range", "/api/climb", dict(pressure_altitude_ft="500", target_alt_ft="12500", oat_c="25"))
    cruise = dict(pressure_altitude_ft="8500", lower_oat_altitude_ft="6000", lower_oat_c="8",
                  upper_oat_altitude_ft="9000", upper_oat_c="2", rpm="2400")
    add("cruise triple interpolation", "/api/cruise", cruise)
    add("profile validation", "/api/aircraft/validate", starter_profile(), True)
    loads = dict(pilot_weight_lbs="180", front_passenger_weight_lbs="205", rear_left_weight_lbs="205",
                 rear_right_weight_lbs="0", baggage1_weight_lbs="0", baggage2_weight_lbs="0",
                 fuel_gal="25", taxi_fuel_gal="1", trip_fuel_gal="12")
    add("GFJE weight balance", "/api/weight-balance", {**loads, "aircraft_profile": json.dumps(starter_profile())})
    ffct = json.dumps(ffct_profile())
    add("FFCT takeoff", "/api/takeoff", {**inputs, "pressure_altitude_ft": "3750", "oat_c": "20", "aircraft_profile": ffct})
    add("FFCT standard landing", "/api/landing", {**inputs, "pressure_altitude_ft": "0", "oat_c": "15", "aircraft_profile": ffct})
    add("FFCT nonstandard landing rejected", "/api/landing", {**inputs, "aircraft_profile": ffct})
    add("FFCT standard cruise", "/api/cruise", {**cruise, "pressure_altitude_ft": "5000",
        "lower_oat_altitude_ft": "2500", "lower_oat_c": "10", "upper_oat_altitude_ft": "7500",
        "upper_oat_c": "0", "aircraft_profile": ffct})
    add("manual table import", "/api/performance/import", dict(phase="landing",
        text="weight_lb,pa_ft,oat_c,ground_ft,total_ft,at_50ft_kias\n2300,0,15,500,1200,60"), True)
    manual = starter_profile()
    manual["performance"] = {phase: builtin_dataset(phase) for phase in ("takeoff", "landing", "cruise")}
    for phase in ("takeoff", "landing"):
        add("manual " + phase, "/api/" + phase, {**inputs, "aircraft_profile": json.dumps(manual)})
    add("manual cruise", "/api/cruise", {**cruise, "aircraft_profile": json.dumps(manual)})
    return result
