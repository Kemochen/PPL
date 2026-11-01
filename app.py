from flask import Flask, jsonify, render_template, request, g
import math
import json

from cruise import estimate_from_oat_bracket
from climb import climb_from_pressure_alt
from landing import landing_distance
from takeoff import takeoff_distance
from weight_balance import calculate_weight_balance
from aircraft import catalogue, starter_profile, ffct_profile, validate_profile, profile_weight_balance
from performance import normalize_performance, import_rows, builtin_dataset, manual_distance, manual_cruise, PHASES
from reference_1974 import reference_distance, reference_cruise, table_view


app = Flask(__name__)


def aircraft_from_form():
    raw = request.form.get("aircraft_profile")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        raise ValueError("Invalid aircraft profile JSON.") from None


@app.before_request
def check_performance_aircraft():
    if request.path not in ("/api/takeoff", "/api/landing", "/api/cruise", "/api/climb"):
        return None
    try:
        raw = aircraft_from_form()
        if raw is not None:
            profile, issues = validate_profile(raw)
            if any("Model year mismatch" in issue for issue in issues):
                raise ValueError("Confirm aircraft year and model before using performance tables.")
            phase = request.path.rsplit("/", 1)[-1]
            if phase == "climb":
                if profile["model_id"] != "c172n":
                    raise ValueError("Climb tables are currently C172N only.")
            else:
                performance, status = normalize_performance(profile["performance"], profile["model_id"])
                if not status[phase]["ready"]:
                    raise ValueError(phase.capitalize() + ": " + "; ".join(status[phase]["issues"]))
                if performance[phase]["mode"] == "manual":
                    g.manual_performance = performance[phase]
                elif performance[phase]["mode"] == "c172m1974":
                    g.reference_1974 = True
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.get("/api/aircraft/models")
def api_aircraft_models():
    return jsonify({"ok": True, "models": catalogue(), "starter_profile": starter_profile(),
                    "starter_profiles": [starter_profile(), ffct_profile()]})


@app.post("/api/aircraft/validate")
def api_aircraft_validate():
    return api_response(lambda: aircraft_validation_result())


def aircraft_validation_result():
    profile, issues = validate_profile(request.get_json(silent=True))
    _, performance_status = normalize_performance(profile["performance"], profile["model_id"])
    return {"profile": profile, "ready": not issues, "issues": issues, "performance_status": performance_status}


@app.post("/api/performance/import")
def api_performance_import():
    def parse():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValueError("A table phase and CSV/TSV text are required.")
        return {"rows": import_rows(data.get("phase"), data.get("text"))}
    return api_response(parse)


@app.get("/api/performance/builtin/<phase>")
def api_performance_builtin(phase):
    if phase not in PHASES:
        return jsonify({"ok": False, "error": "Unknown performance table."}), 400
    return api_response(lambda: builtin_dataset(phase))


@app.get("/api/performance/reference-1974/<phase>")
def api_reference_1974(phase):
    return api_response(lambda: table_view(phase))


def number_value(name, default=0.0):
    value = request.form.get(name, default)
    if value in ("", None):
        return float(default)
    return float(value)


def optional_number(name):
    value = request.form.get(name)
    if value in ("", None):
        return None
    return float(value)


def bool_value(name):
    return request.form.get(name) == "on"


def runway_heading_from_input(value):
    if value is None:
        return None, None
    if 1 <= value <= 36:
        return value * 10, f"Runway {value:02.0f} = {value * 10:.1f} degrees"
    if 0 <= value <= 360:
        return value, f"Runway heading = {value:.1f} degrees"
    raise ValueError("Runway must be 1 to 36, or a heading from 0 to 360 degrees.")


def wind_values_from_form():
    runway_input = optional_number("runway_heading_deg")
    wind_direction = optional_number("wind_direction_deg")
    wind_speed = optional_number("wind_speed_kt")

    if runway_input is None or wind_direction is None or wind_speed is None:
        return {
            "headwind_kt": 0.0,
            "tailwind_kt": 0.0,
            "crosswind_kt": None,
            "steps": [],
        }

    runway_heading, runway_note = runway_heading_from_input(runway_input)
    if not 0 <= wind_direction <= 360:
        raise ValueError("Wind direction must be between 0 and 360 degrees.")
    if not math.isfinite(wind_speed) or wind_speed < 0:
        raise ValueError("Wind speed cannot be negative.")

    reference = request.form.get("wind_reference", "magnetic")
    conversion_steps = []
    if reference == "true":
        variation = optional_number("magnetic_variation_deg")
        variation_direction = request.form.get("variation_direction", "east")
        if variation is None or not math.isfinite(variation) or not 0 <= variation <= 180:
            raise ValueError("Enter airport magnetic variation from 0 to 180 degrees for True wind.")
        if variation_direction not in ("east", "west"):
            raise ValueError("Magnetic variation direction must be east or west.")
        true_direction = wind_direction
        signed_variation = variation if variation_direction == "east" else -variation
        wind_direction = (true_direction - signed_variation) % 360
        operator = "-" if variation_direction == "east" else "+"
        conversion_steps.append({
            "title": "True to magnetic wind direction",
            "formula": "Magnetic = True - East variation, or True + West variation (mod 360)",
            "value": (
                f"({true_direction:.1f} T {operator} {variation:.1f} "
                f"{variation_direction.upper()}) mod 360 = {wind_direction:.1f} M"
            ),
        })
    elif reference == "magnetic":
        conversion_steps.append({
            "title": "Wind direction reference",
            "formula": "Wind and runway use magnetic north",
            "value": f"Wind {wind_direction:.1f} M; no conversion required",
        })
    else:
        raise ValueError("Wind reference must be true or magnetic.")

    wind_angle = abs((wind_direction - runway_heading + 180) % 360 - 180)
    headwind_component = wind_speed * math.cos(math.radians(wind_angle))
    crosswind_component = abs(wind_speed * math.sin(math.radians(wind_angle)))

    headwind_kt = max(headwind_component, 0)
    tailwind_kt = max(-headwind_component, 0)

    steps = [
        {
            "title": "Runway heading",
            "formula": "Runway number x 10 = runway magnetic heading",
            "value": runway_note,
        },
        *conversion_steps,
        {
            "title": "Wind component",
            "formula": "Angle = smallest difference between wind direction and runway heading",
            "value": (
                f"Wind {wind_direction:.1f} M, runway {runway_heading:.1f} M: smallest angle = "
                f"{wind_angle:.1f} degrees"
            ),
        },
        {
            "title": "Headwind component",
            "formula": "Headwind = wind speed x cos(angle)",
            "value": (
                f"{wind_speed:.1f} x cos({wind_angle:.1f}) = "
                f"{headwind_component:.1f} kt"
            ),
        },
        {
            "title": "Crosswind component",
            "formula": "Crosswind = wind speed x sin(angle)",
            "value": (
                f"{wind_speed:.1f} x sin({wind_angle:.1f}) = "
                f"{crosswind_component:.1f} kt"
            ),
        },
        {
            "title": "Wind used",
            "formula": "Positive component = headwind, negative component = tailwind",
            "value": f"HW {headwind_kt:.1f} kt, TW {tailwind_kt:.1f} kt",
        },
    ]

    return {
        "headwind_kt": headwind_kt,
        "tailwind_kt": tailwind_kt,
        "crosswind_kt": crosswind_component,
        "steps": steps,
    }


def api_response(calculator):
    try:
        result = calculator()
        steps = []
        if isinstance(result, dict):
            steps = result.pop("calculation_steps", [])
        return jsonify({"ok": True, "result": result, "steps": steps})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Unexpected error: {exc}"}), 500


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/takeoff")
def api_takeoff():
    try:
        wind = wind_values_from_form()
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    if getattr(g, "reference_1974", False):
        return api_response(lambda: reference_distance("takeoff", number_value("weight_lbs"),
            number_value("pressure_altitude_ft"), number_value("oat_c"), wind, bool_value("grass")))
    if getattr(g, "manual_performance", None) is not None:
        return api_response(lambda: manual_distance(g.manual_performance, "takeoff", number_value("weight_lbs"),
            number_value("pressure_altitude_ft"), number_value("oat_c"), wind, bool_value("grass")))
    return api_response(lambda: takeoff_distance(
        weight_lbs=number_value("weight_lbs"),
        pressure_altitude_ft=number_value("pressure_altitude_ft"),
        oat_c=number_value("oat_c"),
        headwind_kt=wind["headwind_kt"],
        tailwind_kt=wind["tailwind_kt"],
        crosswind_kt=wind["crosswind_kt"],
        wind_steps=wind["steps"],
        grass=bool_value("grass"),
    ))


@app.post("/api/landing")
def api_landing():
    try:
        wind = wind_values_from_form()
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    if getattr(g, "reference_1974", False):
        return api_response(lambda: reference_distance("landing", number_value("weight_lbs"),
            number_value("pressure_altitude_ft"), number_value("oat_c"), wind, bool_value("grass")))
    if getattr(g, "manual_performance", None) is not None:
        return api_response(lambda: manual_distance(g.manual_performance, "landing", number_value("weight_lbs"),
            number_value("pressure_altitude_ft"), number_value("oat_c"), wind, bool_value("grass")))
    return api_response(lambda: landing_distance(
        pressure_altitude_ft=number_value("pressure_altitude_ft"),
        oat_c=number_value("oat_c"),
        headwind_kt=wind["headwind_kt"],
        tailwind_kt=wind["tailwind_kt"],
        crosswind_kt=wind["crosswind_kt"],
        wind_steps=wind["steps"],
        grass=bool_value("grass"),
    ))


@app.post("/api/cruise")
def api_cruise():
    if getattr(g, "reference_1974", False):
        return api_response(lambda: reference_cruise(number_value("pressure_altitude_ft"),
            number_value("lower_oat_altitude_ft"), number_value("lower_oat_c"),
            number_value("upper_oat_altitude_ft"), number_value("upper_oat_c"), number_value("rpm")))
    if getattr(g, "manual_performance", None) is not None:
        return api_response(lambda: manual_cruise(g.manual_performance, number_value("pressure_altitude_ft"),
            number_value("lower_oat_altitude_ft"), number_value("lower_oat_c"),
            number_value("upper_oat_altitude_ft"), number_value("upper_oat_c"), number_value("rpm")))
    return api_response(lambda: estimate_from_oat_bracket(
        alt_ft=number_value("pressure_altitude_ft"),
        lower_alt_ft=number_value("lower_oat_altitude_ft"),
        lower_oat_c=number_value("lower_oat_c"),
        upper_alt_ft=number_value("upper_oat_altitude_ft"),
        upper_oat_c=number_value("upper_oat_c"),
        rpm=number_value("rpm"),
    ))


@app.post("/api/climb")
def api_climb():
    return api_response(lambda: climb_from_pressure_alt(
        pressure_alt_ft=number_value("pressure_altitude_ft"),
        target_alt_ft=number_value("target_altitude_ft"),
        oat_c=number_value("oat_c"),
    ))


@app.post("/api/weight-balance")
def api_weight_balance():
    if request.form.get("aircraft_profile"):
        return api_response(lambda: profile_weight_balance(
            aircraft_from_form(),
            {key: number_value(key) for key in (
                "pilot_weight_lbs", "front_passenger_weight_lbs", "rear_left_weight_lbs",
                "rear_right_weight_lbs", "baggage1_weight_lbs", "baggage2_weight_lbs",
                "fuel_gal", "taxi_fuel_gal", "trip_fuel_gal")},
        ))
    return api_response(lambda: calculate_weight_balance(
        empty_weight_lbs=number_value("empty_weight_lbs", 1541),
        empty_arm_in=number_value("empty_arm_in", 38.2),
        pilot_weight_lbs=number_value("pilot_weight_lbs"),
        front_passenger_weight_lbs=number_value("front_passenger_weight_lbs"),
        rear_left_weight_lbs=number_value("rear_left_weight_lbs"),
        rear_right_weight_lbs=number_value("rear_right_weight_lbs"),
        baggage1_weight_lbs=number_value("baggage1_weight_lbs"),
        baggage2_weight_lbs=number_value("baggage2_weight_lbs"),
        fuel_gal=number_value("fuel_gal"),
        taxi_fuel_gal=number_value("taxi_fuel_gal"),
        trip_fuel_gal=number_value("trip_fuel_gal"),
    ))


if __name__ == "__main__":
    app.run(debug=True)
