from flask import Flask, jsonify, render_template, request
import math

from cruise import estimate_from_oat_bracket
from landing import landing_distance
from takeoff import takeoff_distance


app = Flask(__name__)


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
    if wind_speed < 0:
        raise ValueError("Wind speed cannot be negative.")

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
        {
            "title": "Wind component",
            "formula": "Angle = smallest difference between wind direction and runway heading",
            "value": (
                f"|{wind_direction:.1f} - {runway_heading:.1f}| = "
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
    wind = wind_values_from_form()
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
    wind = wind_values_from_form()
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
    return api_response(lambda: estimate_from_oat_bracket(
        alt_ft=number_value("pressure_altitude_ft"),
        lower_alt_ft=number_value("lower_oat_altitude_ft"),
        lower_oat_c=number_value("lower_oat_c"),
        upper_alt_ft=number_value("upper_oat_altitude_ft"),
        upper_oat_c=number_value("upper_oat_c"),
        rpm=number_value("rpm"),
    ))


if __name__ == "__main__":
    app.run(debug=True)
