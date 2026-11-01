"""Aircraft identity catalogue and user-supplied, tail-specific W&B profiles."""

from copy import deepcopy
import math
from performance import default_performance, normalize_performance


TCDS_172 = "https://aerovalley.org/wp-content/uploads/2023/07/Cessna_type_cert.pdf"
PIPER_SOURCE = "https://www.piper.com/technical-publications/"
DIAMOND_SOURCE = "https://www.diamondaircraft.com/en/private-owners/aircraft/da40/tech-specs/"
STATIONS = [
    ("pilot_weight_lbs", "Pilot"),
    ("front_passenger_weight_lbs", "Front Passenger"),
    ("rear_left_weight_lbs", "Rear Left"),
    ("rear_right_weight_lbs", "Rear Right"),
    ("baggage1_weight_lbs", "Baggage 1"),
    ("baggage2_weight_lbs", "Baggage 2"),
]


def model(model_id, name, seats, source, years=None, **wb):
    return dict(id=model_id, name=name, seats=seats, source=source,
                years=years, wb=wb, performance_available=model_id == "c172n",
                performance_label={"c172n": "C172N", "c172m": "C172M (1974 reference)"}.get(model_id))


CATALOGUE = [
    model("c150m", "Cessna 150M", 2, "https://cessna150152club.org/aircraft-specifications-2/"),
    model("c152", "Cessna 152", 2, "https://cessna150152club.org/aircraft-specifications-2/"),
    model("c172l", "Cessna 172L", 4, TCDS_172, [1971, 1972], max_takeoff_lb=2300, max_landing_lb=2300, usable_fuel_gal=38, forward_at_max=38.5),
    model("c172m", "Cessna 172M", 4, TCDS_172, [1973, 1976], max_takeoff_lb=2300, max_landing_lb=2300, forward_at_max=38.5),
    model("c172n", "Cessna 172N", 4, TCDS_172, [1977, 1980], max_takeoff_lb=2300, max_landing_lb=2300, forward_at_max=38.5),
    model("c172p", "Cessna 172P", 4, TCDS_172, [1981, 1986], max_takeoff_lb=2400, max_landing_lb=2400, forward_at_max=39.5),
    model("c172r", "Cessna 172R (standard 160 hp)", 4, TCDS_172, max_ramp_lb=2457, max_takeoff_lb=2450, max_landing_lb=2450, usable_fuel_gal=53, forward_at_max=40),
    model("c172s", "Cessna 172S / Skyhawk SP", 4, TCDS_172, max_ramp_lb=2558, max_takeoff_lb=2550, max_landing_lb=2550, usable_fuel_gal=53, forward_at_max=41),
    model("c182t", "Cessna 182T / Skylane", 4, "https://cessna.txtav.com/en/piston/cessna-skylane"),
    model("pa28-140", "Piper PA-28-140 / Cherokee", 4, PIPER_SOURCE),
    model("pa28-161", "Piper PA-28-161 / Warrior", 4, PIPER_SOURCE),
    model("pa28-181", "Piper PA-28-181 / Archer", 4, PIPER_SOURCE),
    model("da20-c1", "Diamond DA20-C1", 2, "https://info.diamondair.com/Brochure_DA20-C1_2023.pdf"),
    model("da40-xlt", "Diamond DA40 XLT (AVGAS)", 4, DIAMOND_SOURCE),
    model("da40-ng", "Diamond DA40 NG (Jet fuel)", 4, DIAMOND_SOURCE),
    model("custom", "Other / Custom aircraft", 4, ""),
]
MODELS = {entry["id"]: entry for entry in CATALOGUE}


def blank_profile(model_id):
    entry = MODELS.get(model_id)
    if entry is None:
        raise ValueError("Unknown aircraft model.")
    cessna172 = model_id.startswith("c172")
    defaults = entry["wb"]
    stations = []
    for i, (key, label) in enumerate(STATIONS):
        enabled = not (entry["seats"] == 2 and i in (2, 3))
        if i == 5 and model_id in ("c172l", "c172m", "c172n", "c172p"):
            enabled = False
        arm = [40, 40, 73, 73, 95, 123][i] if cessna172 else None
        stations.append(dict(key=key, label=label, arm_in=arm, enabled=enabled,
                             max_weight_lb=120 if cessna172 and i == 4 else (50 if cessna172 and i == 5 else None)))
    envelope = []
    if cessna172:
        envelope = [dict(weight_lb=0, forward_in=35, aft_in=47.3),
                    dict(weight_lb=1950, forward_in=35, aft_in=47.3),
                    dict(weight_lb=defaults["max_takeoff_lb"], forward_in=defaults["forward_at_max"], aft_in=47.3)]
    return dict(id="", name=entry["name"], model_id=model_id, registration="",
                serial_number="", year=None, wb_reference="", wb_date="", notes="",
                performance=default_performance(model_id),
                wb=dict(empty_weight_lb=None, empty_moment_lb_in=None,
                        fuel_density_lb_gal=None if model_id == "da40-ng" else 6,
                        fuel_arm_in=48 if cessna172 else None,
                        max_ramp_lb=defaults.get("max_ramp_lb"),
                        max_takeoff_lb=defaults.get("max_takeoff_lb"),
                        max_landing_lb=defaults.get("max_landing_lb"),
                        usable_fuel_gal=defaults.get("usable_fuel_gal"),
                        baggage_total_lb=120 if cessna172 else None,
                        stations=stations, cg_limits=envelope))


def catalogue():
    return [dict(entry, template=blank_profile(entry["id"])) for entry in CATALOGUE]


def starter_profile():
    profile = blank_profile("c172n")
    profile.update(id="aircraft-c-gfje", name="Cessna 172N (1979)", registration="C-GFJE",
                   serial_number="17272818", year=1979,
                   wb_reference="GFJE W&B values supplied by user in the existing calculator",
                   notes="Identity: operator lists C-GFJE as C172N: https://compassflying.com/fleet/\n"
                         "Registration mirror (CCAR snapshot 2026-01-20): serial 17272818, year 1979: "
                         "https://www.regosearch.com/aircraft/ca/GFJE\n"
                         "Serial falls within 1979 C172N model range in FAA TCDS 3A12. "
                         "User confirmed the existing calculator's W&B data belongs to GFJE. "
                         "Usable fuel defaults to the standard 40 US gal configuration; editable for this aircraft.")
    profile["wb"].update(empty_weight_lb=1541, empty_moment_lb_in=1541 * 38.2,
                         max_ramp_lb=2307, usable_fuel_gal=40)
    profile["wb"]["stations"][5]["enabled"] = True
    return profile


def ffct_profile():
    from reference_1974 import conditions, SOURCE_URL
    profile = blank_profile("c172m")
    profile.update(id="aircraft-c-ffct", name="Cessna 172M (1974)", registration="C-FFCT",
                   serial_number="17262961", year=1974,
                   notes="Operator identifies C-FFCT as C172M: https://compassflying.com/fleet/\n"
                         "CCAR mirror snapshot 2026-06-30: C172M, serial 17262961, manufactured 1974: https://www.regosearch.com/aircraft/ca/FFCT\n"
                         "Performance is a 1974 stock-aircraft REFERENCE from the AAFC N9850V scan, not FFCT's confirmed POH. "
                         "Check FFCT's actual manual, propeller and STCs. "
                         "Empty weight/moment and tank option are not known; no GFJE W&B values copied.")
    for phase in ("takeoff", "landing", "cruise"):
        profile["performance"][phase].update(mode="c172m1974", source="1974 reference: " + SOURCE_URL,
                                              conditions=conditions(phase))
    return profile


def validate_profile(raw):
    if not isinstance(raw, dict) or raw.get("model_id") not in MODELS:
        raise ValueError("Choose an aircraft model from the catalogue.")
    result = blank_profile(raw["model_id"])
    issues = []
    for key in ("id", "name", "registration", "serial_number", "wb_reference", "wb_date", "notes"):
        value = raw.get(key, "")
        if not isinstance(value, str) or len(value) > 2000:
            raise ValueError(f"Invalid aircraft field: {key}.")
        result[key] = value.strip()
    if not result["name"]:
        raise ValueError("Aircraft name is required.")

    def numeric(value, label, required=True, positive=False):
        if value is None or value == "":
            if required:
                issues.append(f"{label}: required")
            return None
        if isinstance(value, bool):
            raise ValueError(f"{label}: enter a finite number.")
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{label}: enter a finite number.") from None
        if not math.isfinite(value):
            raise ValueError(f"{label}: enter a finite number.")
        if positive and value <= 0:
            raise ValueError(f"{label}: must be greater than zero.")
        return value

    year = numeric(raw.get("year"), "Year", required=False)
    if year is not None and (year != int(year) or not 1900 <= year <= 2100):
        raise ValueError("Enter a four-digit aircraft year.")
    result["year"] = int(year) if year is not None else None
    years = MODELS[result["model_id"]]["years"]
    if year and years and not years[0] <= year <= years[1]:
        issues.append(f"Model year mismatch: {MODELS[result['model_id']]['name']} is listed for {years[0]}-{years[1]}. Confirm serial number and model.")
    if not result["registration"]:
        issues.append("Registration: required for an aircraft profile")
    if not result["wb_reference"]:
        issues.append("Aircraft W&B document / POH reference: required")
    supplied = raw.get("wb")
    if not isinstance(supplied, dict):
        raise ValueError("Aircraft W&B configuration is required.")
    wb = result["wb"]
    for key in ("empty_weight_lb", "empty_moment_lb_in", "fuel_density_lb_gal", "fuel_arm_in",
                "max_ramp_lb", "max_takeoff_lb", "max_landing_lb", "usable_fuel_gal", "baggage_total_lb"):
        wb[key] = numeric(supplied.get(key), key, positive=key in (
            "empty_weight_lb", "fuel_density_lb_gal", "max_ramp_lb", "max_takeoff_lb", "max_landing_lb"))
    for key in ("usable_fuel_gal", "baggage_total_lb"):
        if wb[key] is not None and wb[key] < 0:
            raise ValueError(f"{key}: cannot be negative.")
    if wb["max_ramp_lb"] and wb["max_takeoff_lb"] and wb["max_ramp_lb"] < wb["max_takeoff_lb"]:
        raise ValueError("Maximum ramp weight cannot be below maximum takeoff weight.")
    supplied_stations = supplied.get("stations", [])
    if not isinstance(supplied_stations, list) or len(supplied_stations) != len(STATIONS):
        raise ValueError("Six loading station definitions are required.")
    for station, expected in zip(supplied_stations, wb["stations"]):
        if not isinstance(station, dict) or station.get("key") != expected["key"]:
            raise ValueError("Loading stations do not match the required order.")
        if not isinstance(station.get("enabled"), bool):
            raise ValueError("Loading station enabled must be true or false.")
        expected["enabled"] = station["enabled"]
        expected["arm_in"] = numeric(station.get("arm_in"), expected["label"] + " arm", required=expected["enabled"])
        expected["max_weight_lb"] = numeric(station.get("max_weight_lb"), expected["label"] + " limit", required=False)
        if expected["max_weight_lb"] is not None and expected["max_weight_lb"] < 0:
            raise ValueError("Station weight limits cannot be negative.")
    limits = supplied.get("cg_limits", [])
    if not isinstance(limits, list) or len(limits) > 30:
        raise ValueError("CG envelope must contain at most 30 rows.")
    wb["cg_limits"] = []
    for row in limits:
        if not isinstance(row, dict):
            raise ValueError("Invalid CG envelope row.")
        point = {key: numeric(row.get(key), "CG " + key) for key in ("weight_lb", "forward_in", "aft_in")}
        if all(value is not None for value in point.values()):
            if point["weight_lb"] < 0 or point["forward_in"] >= point["aft_in"]:
                raise ValueError("CG rows need nonnegative weight and forward limit below aft limit.")
            wb["cg_limits"].append(point)
    points = wb["cg_limits"]
    if len(points) < 2:
        issues.append("CG envelope: at least two complete weight / forward / aft rows required")
    if any(a["weight_lb"] >= b["weight_lb"] for a, b in zip(points, points[1:])):
        raise ValueError("CG envelope weights must be strictly increasing.")
    if points and wb["max_takeoff_lb"] and points[-1]["weight_lb"] < wb["max_takeoff_lb"]:
        issues.append("CG envelope must cover maximum takeoff weight")
    if points and wb["max_landing_lb"] and points[-1]["weight_lb"] < wb["max_landing_lb"]:
        issues.append("CG envelope must cover maximum landing weight")
    result["performance"], _ = normalize_performance(raw.get("performance"), result["model_id"])
    if any(dataset["mode"] == "c172m1974" for dataset in result["performance"].values()) and result["year"] != 1974:
        issues.append("Model year mismatch: 1974 reference data requires model year 1974")
    return result, issues


def require_profile(raw):
    profile, issues = validate_profile(raw)
    if issues:
        raise ValueError("Complete aircraft profile: " + "; ".join(issues))
    return profile


def cg_at_weight(points, weight):
    if weight <= points[0]["weight_lb"]:
        return points[0]["forward_in"], points[0]["aft_in"]
    for low, high in zip(points, points[1:]):
        if weight <= high["weight_lb"]:
            fraction = (weight - low["weight_lb"]) / (high["weight_lb"] - low["weight_lb"])
            return tuple(low[key] + fraction * (high[key] - low[key]) for key in ("forward_in", "aft_in"))
    return points[-1]["forward_in"], points[-1]["aft_in"]


def profile_weight_balance(raw, loads):
    profile = require_profile(raw)
    wb = profile["wb"]
    loads = deepcopy(loads)
    for key, value in loads.items():
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{key}: enter a finite nonnegative load.")
    if loads["taxi_fuel_gal"] + loads["trip_fuel_gal"] > loads["fuel_gal"] + 1e-9:
        raise ValueError("Taxi plus trip fuel cannot exceed fuel on board.")
    rows, steps = [], []

    def add_load(label, arm, weight, moment=None, kind="load"):
        moment = weight * arm if moment is None else moment
        rows.append(dict(item=label, arm=arm, weight=weight, moment=moment, cg=None, kind=kind))
        steps.append(dict(title="Moment - " + label, formula="Moment = weight x arm", value=f"{weight:.1f} x {arm:.1f} = {moment:.1f} lb-in"))
        return weight, moment

    empty_weight, empty_moment = wb["empty_weight_lb"], wb["empty_moment_lb_in"]
    add_load("Empty Aircraft", empty_moment / empty_weight, empty_weight, empty_moment)
    weight, moment = empty_weight, empty_moment
    loading_errors = []
    for station in wb["stations"]:
        load = loads[station["key"]]
        if not station["enabled"]:
            if load:
                raise ValueError(station["label"] + " is not enabled for this aircraft.")
            continue
        if station["max_weight_lb"] is not None and load > station["max_weight_lb"]:
            loading_errors.append(station["label"] + " OVER LIMIT")
        load_weight, load_moment = add_load(station["label"], station["arm_in"], load)
        weight += load_weight
        moment += load_moment
    if loads["baggage1_weight_lbs"] + loads["baggage2_weight_lbs"] > wb["baggage_total_lb"]:
        loading_errors.append("COMBINED BAGGAGE OVER LIMIT")
    if loads["fuel_gal"] > wb["usable_fuel_gal"]:
        loading_errors.append("FUEL EXCEEDS USABLE CAPACITY")
    phases, explanations = [], []

    def add_phase(label, max_weight, previous=None, change_weight=0, change_moment=0):
        if weight <= 0:
            raise ValueError("Phase weight must be greater than zero.")
        cg = moment / weight
        rows.append(dict(item="Zero Fuel" if label == "ZFW" else label, arm=None, weight=weight, moment=moment, cg=cg, kind="total"))
        forward, aft = cg_at_weight(wb["cg_limits"], weight)
        errors = list(loading_errors)
        if max_weight is not None and weight > max_weight:
            errors.append(f"OVER MAX {label.upper()} WEIGHT")
        if weight < wb["cg_limits"][0]["weight_lb"]:
            errors.append("BELOW CG ENVELOPE WEIGHT RANGE")
        if label != "Ramp" and weight > wb["cg_limits"][-1]["weight_lb"]:
            errors.append("ABOVE CG ENVELOPE WEIGHT RANGE")
        if cg < forward:
            errors.append("CG FORWARD OF LIMIT")
        if cg > aft:
            errors.append("CG AFT OF LIMIT")
        message = "; ".join(errors) or ("CG within limits; no separate ZFW weight limit configured" if label == "ZFW" else "Within configured limits")
        phases.append(dict(phase=label, weight=weight, max_weight=max_weight, cg=cg,
                           forward_limit=forward, aft_limit=aft, limit=f"{forward:.1f} - {aft:.1f}",
                           status="FAIL" if errors else "OK", message=message))
        lines = [f"Weight = {weight:.1f} lb", f"Moment = {moment:.1f} lb-in"]
        if previous:
            lines = [f"Weight: {previous[0]:.1f} + ({change_weight:.1f}) = {weight:.1f} lb",
                     f"Moment: {previous[1]:.1f} + ({change_moment:.1f}) = {moment:.1f} lb-in"]
        else:
            lines = [f"Weight: " + " + ".join(f"{row['weight']:.1f}" for row in rows if row["kind"] == "load") + f" = {weight:.1f} lb",
                     f"Moment: " + " + ".join(f"{row['moment']:.1f}" for row in rows if row["kind"] == "load") + f" = {moment:.1f} lb-in"]
        lines.append(f"CG: {moment:.1f} / {weight:.1f} = {cg:.1f} in")
        explanations.append(dict(title=label, lines=lines))
        steps.append(dict(title=label, formula="CG = total moment / total weight", value="; ".join(lines)))

    add_phase("ZFW", None)
    for label, fuel_key, sign, max_weight in (
        ("Ramp", "fuel_gal", 1, wb["max_ramp_lb"]),
        ("Takeoff", "taxi_fuel_gal", -1, wb["max_takeoff_lb"]),
        ("Landing", "trip_fuel_gal", -1, wb["max_landing_lb"]),
    ):
        fuel_weight = loads[fuel_key] * wb["fuel_density_lb_gal"]
        steps.append(dict(title=f"{fuel_key} conversion", formula="Fuel weight = US gal x lb/US gal",
                          value=f"{loads[fuel_key]:.1f} x {wb['fuel_density_lb_gal']:.1f} = {fuel_weight:.1f} lb"))
        previous = weight, moment
        delta_weight, delta_moment = add_load({"Ramp": "Fuel", "Takeoff": "Taxi Fuel", "Landing": "Trip Fuel"}[label],
                                              wb["fuel_arm_in"], sign * fuel_weight, kind="load" if sign == 1 else "burn")
        weight += delta_weight
        moment += delta_moment
        add_phase(label, max_weight, previous, delta_weight, delta_moment)
    points = wb["cg_limits"]
    floor = max(points[0]["weight_lb"], min(min(p["weight"] for p in phases) * 0.85,
                                           points[-1]["weight_lb"] * 0.8))
    forward, aft = cg_at_weight(points, floor)
    envelope = [dict(cg=forward, weight=floor)]
    envelope += [dict(cg=p["forward_in"], weight=p["weight_lb"]) for p in points if p["weight_lb"] > floor]
    envelope += [dict(cg=p["aft_in"], weight=p["weight_lb"]) for p in reversed(points) if p["weight_lb"] > floor]
    envelope.append(dict(cg=aft, weight=floor))
    return dict(kind="weight_balance", aircraft_name=profile["name"], registration=profile["registration"],
                summary=dict(zero_fuel_cg_in=phases[0]["cg"], ramp_cg_in=phases[1]["cg"],
                             takeoff_cg_in=phases[2]["cg"], landing_cg_in=phases[3]["cg"],
                             takeoff_weight_lbs=phases[2]["weight"], landing_weight_lbs=phases[3]["weight"]),
                rows=rows, envelope=phases, explanations=explanations,
                plot=dict(envelope=envelope, points=[dict(label=p["phase"], cg=p["cg"], weight=p["weight"], status=p["status"]) for p in phases]),
                calculation_steps=steps)
