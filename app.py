from flask import Flask, jsonify, render_template, request

from C import estimate_from_sea_level_oat
from L import landing_distance
from T import takeoff_distance


app = Flask(__name__)


def number_value(name, default=0.0):
    value = request.form.get(name, default)
    if value in ("", None):
        return float(default)
    return float(value)


def bool_value(name):
    return request.form.get(name) == "on"


def api_response(calculator):
    try:
        return jsonify({"ok": True, "result": calculator()})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Unexpected error: {exc}"}), 500


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/takeoff")
def api_takeoff():
    return api_response(lambda: takeoff_distance(
        weight_lbs=number_value("weight_lbs"),
        pressure_altitude_ft=number_value("pressure_altitude_ft"),
        oat_c=number_value("oat_c"),
        headwind_kt=number_value("headwind_kt"),
        tailwind_kt=number_value("tailwind_kt"),
        grass=bool_value("grass"),
    ))


@app.post("/api/landing")
def api_landing():
    return api_response(lambda: landing_distance(
        pressure_altitude_ft=number_value("pressure_altitude_ft"),
        oat_c=number_value("oat_c"),
        headwind_kt=number_value("headwind_kt"),
        tailwind_kt=number_value("tailwind_kt"),
        grass=bool_value("grass"),
    ))


@app.post("/api/cruise")
def api_cruise():
    return api_response(lambda: estimate_from_sea_level_oat(
        alt_ft=number_value("pressure_altitude_ft"),
        sea_level_oat_c=number_value("sea_level_oat_c"),
        rpm=number_value("rpm"),
    ))


if __name__ == "__main__":
    app.run(debug=True)
