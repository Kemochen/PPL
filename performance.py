"""Validated, profile-owned POH tables; calculations never mutate built-in tables."""

import csv
import io
import math

from cruise import bracket, isa_temp_c
from takeoff import interpolation_steps


PHASES = ("takeoff", "landing", "cruise")
COLUMNS = {
    "takeoff": ("weight_lb", "pa_ft", "oat_c", "ground_ft", "total_ft", "lift_off_kias", "at_50ft_kias"),
    "landing": ("weight_lb", "pa_ft", "oat_c", "ground_ft", "total_ft", "at_50ft_kias"),
    "cruise": ("pa_ft", "isa_offset_c", "rpm", "percent_bhp", "ktas", "gph"),
}
RULE_FIELDS = ("headwind_pct", "headwind_step_kt", "headwind_max_kt",
               "tailwind_pct", "tailwind_step_kt", "tailwind_max_kt", "grass_pct")


def empty_dataset(mode="none"):
    return dict(mode=mode, source="", conditions="", reference_weight_lb=None,
                grass_mode="none", rows=[], **{key: None for key in RULE_FIELDS})


def default_performance(model_id):
    return {phase: empty_dataset("builtin" if model_id == "c172n" else "none") for phase in PHASES}


def number(value, label, optional=False):
    if value in (None, ""):
        if optional:
            return None
        raise ValueError(f"{label}: a number is required.")
    if isinstance(value, bool):
        raise ValueError(f"{label}: enter a finite number.")
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label}: enter a finite number.") from None
    if not math.isfinite(value):
        raise ValueError(f"{label}: enter a finite number.")
    return value


def validate_dataset(raw, phase, model_id):
    if not isinstance(raw, dict):
        raise ValueError(f"{phase}: invalid performance dataset.")
    result = empty_dataset()
    result["mode"] = raw.get("mode", "none")
    if result["mode"] not in ("none", "builtin", "manual", "c172m1974"):
        raise ValueError(f"{phase}: invalid dataset mode.")
    for key in ("source", "conditions"):
        value = raw.get(key, "")
        if not isinstance(value, str) or len(value) > 2000:
            raise ValueError(f"{phase}: invalid {key}.")
        result[key] = value.strip()
    result["reference_weight_lb"] = number(raw.get("reference_weight_lb"), f"{phase} reference weight", True)
    if result["reference_weight_lb"] is not None and result["reference_weight_lb"] <= 0:
        raise ValueError("Reference weight must be greater than zero.")
    for key in RULE_FIELDS:
        result[key] = number(raw.get(key), f"{phase} {key}", True)
        if result[key] is not None and result[key] < 0:
            raise ValueError(f"{phase} {key} cannot be negative.")
    for key in ("headwind_pct", "tailwind_pct", "grass_pct"):
        if result[key] is not None and result[key] > 100:
            raise ValueError(f"{phase} {key} must be 0 to 100 percent.")
    result["grass_mode"] = raw.get("grass_mode", "none")
    if result["grass_mode"] not in ("none", "ground_add", "both_percent"):
        raise ValueError(f"{phase}: invalid grass correction mode.")
    rows = raw.get("rows", [])
    if not isinstance(rows, list) or len(rows) > 3000:
        raise ValueError(f"{phase}: at most 3000 table rows are allowed.")
    issues, seen = [], set()
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f"{phase} row {index}: invalid table row.")
        parsed = {key: number(row.get(key), f"{phase} row {index} {key}", True) for key in COLUMNS[phase]}
        result["rows"].append(parsed)
        if any(value is None for value in parsed.values()):
            issues.append(f"Row {index}: fill every cell")
            continue
        for key, value in parsed.items():
            if key not in ("pa_ft", "oat_c", "isa_offset_c") and value <= 0:
                raise ValueError(f"{phase} row {index}: {key} must be greater than zero.")
        if phase == "cruise" and parsed["percent_bhp"] > 100:
            raise ValueError("Cruise power cannot exceed 100 percent BHP.")
        if phase != "cruise" and parsed["total_ft"] < parsed["ground_ft"]:
            raise ValueError(f"{phase} row {index}: 50 ft distance cannot be below ground roll.")
        key_fields = ("pa_ft", "isa_offset_c", "rpm") if phase == "cruise" else ("weight_lb", "pa_ft", "oat_c")
        coordinate = tuple(parsed[key] for key in key_fields)
        if coordinate in seen:
            raise ValueError(f"{phase} row {index}: duplicate table coordinates.")
        seen.add(coordinate)
    if result["mode"] == "none":
        return result, ["No performance dataset selected"]
    if result["mode"] == "builtin":
        return result, ([] if model_id == "c172n" else ["Built-in data is C172N only"])
    if result["mode"] == "c172m1974":
        return result, ([] if model_id == "c172m" else ["1974 reference data is C172M only"])
    for key in ("source", "conditions"):
        if not result[key]:
            issues.append(f"POH {key} is required")
    if not rows:
        issues.append("Enter at least one complete table row")
    if phase == "cruise":
        if result["reference_weight_lb"] is None:
            issues.append("Cruise table reference weight is required")
    else:
        for kind in ("headwind", "tailwind"):
            fields = [result[kind + suffix] for suffix in ("_pct", "_step_kt", "_max_kt")]
            if any(value is not None for value in fields):
                if fields[0] is None or fields[1] is None or fields[1] <= 0 or (fields[2] is not None and fields[2] <= 0):
                    issues.append(f"{kind}: enter percent and a positive knot step; a recorded maximum must be positive")
        if result["grass_mode"] != "none" and result["grass_pct"] is None:
            issues.append("Enter grass correction percent")
        if not any(value is None for row in result["rows"] for value in row.values()):
            for weight in {row["weight_lb"] for row in result["rows"]}:
                group = [row for row in result["rows"] if row["weight_lb"] == weight]
                if len(group) != len({row["pa_ft"] for row in group}) * len({row["oat_c"] for row in group}):
                    issues.append(f"{weight:.1f} lb table: altitude / OAT grid has missing cells")
    return result, issues


def normalize_performance(raw, model_id):
    if raw is None:
        raw = default_performance(model_id)
    if not isinstance(raw, dict):
        raise ValueError("Invalid aircraft performance configuration.")
    result, status = {}, {}
    for phase in PHASES:
        result[phase], issues = validate_dataset(raw.get(phase, empty_dataset()), phase, model_id)
        status[phase] = dict(ready=not issues, mode=result[phase]["mode"], issues=issues)
    return result, status


def import_rows(phase, text):
    if phase not in PHASES or not isinstance(text, str) or len(text) > 1000000:
        raise ValueError("Choose a phase and a CSV/TSV table smaller than 1 MB.")
    text = text.lstrip("\ufeff").strip()
    if not text:
        raise ValueError("The table is empty.")
    delimiter = "\t" if "\t" in text.splitlines()[0] else ","
    try:
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter, strict=True)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames) or set(reader.fieldnames) != set(COLUMNS[phase]):
            raise ValueError("Expected header: " + ",".join(COLUMNS[phase]))
        rows = []
        for index, row in enumerate(reader, 2):
            if len(rows) >= 3000 or None in row or any(value is None for value in row.values()):
                raise ValueError(f"CSV row {index}: wrong number of cells or too many rows.")
            rows.append({key: number(row[key].strip(), f"CSV row {index} {key}") for key in COLUMNS[phase]})
        if not rows:
            raise ValueError("The table contains no data rows.")
        probe = empty_dataset("manual")
        probe.update(rows=rows)
        validate_dataset(probe, phase, "custom")
        return rows
    except csv.Error as exc:
        raise ValueError("Invalid CSV: " + str(exc)) from None


def builtin_dataset(phase):
    import takeoff
    import landing
    import cruise
    result = empty_dataset("manual")
    result["source"] = "Existing C172N calculator table - enter matching POH edition / figure / page"
    result["conditions"] = "C172N; verify aircraft configuration and POH conditions"
    if phase == "cruise":
        result["reference_weight_lb"] = 2300
        result["conditions"] = "2300 lb; recommended lean mixture"
        result["rows"] = [dict(zip(COLUMNS[phase], (alt, temperature, rpm, *value))) for (alt, rpm, temperature), value in sorted(cruise.data.items())]
    else:
        result.update(headwind_pct=10, headwind_step_kt=9, headwind_max_kt=None,
                      tailwind_pct=10, tailwind_step_kt=2, tailwind_max_kt=10,
                      grass_mode="ground_add", grass_pct=15 if phase == "takeoff" else 45)
        if phase == "takeoff":
            for weight, table in sorted(takeoff.tables.items()):
                for i, altitude in enumerate(takeoff.alts):
                    for j, temp in enumerate(takeoff.temps):
                        result["rows"].append(dict(zip(COLUMNS[phase], (weight, float(altitude), float(temp), float(table["ground"][i, j]), float(table["total"][i, j]), table["lift_off"], table["at_50ft"]))))
        else:
            for i, altitude in enumerate(landing.alts):
                for j, temp in enumerate(landing.temps):
                    result["rows"].append(dict(zip(COLUMNS[phase], (2300, float(altitude), float(temp), float(landing.ground_roll[i, j]), float(landing.total_50ft[i, j]), 60))))
    return result


def mix(x, low, high, first, last):
    return first if low == high else first + (x - low) / (high - low) * (last - first)


def linear_math(x, low, high, first, last):
    value = mix(x, low, high, first, last)
    if low == high:
        return f"Exact {x:.1f}: {value:.1f}"
    return f"{first:.1f} + ({x:.1f} - {low:.1f}) / ({high:.1f} - {low:.1f}) x ({last:.1f} - {first:.1f}) = {value:.1f}"


def source_step(dataset):
    return dict(title="POH data source", formula=dataset["source"], value=dataset["conditions"])


def grid_value(rows, field, pa, oat):
    alt_low, alt_high = bracket(sorted({row["pa_ft"] for row in rows}), pa, "Pressure altitude")
    temp_low, temp_high = bracket(sorted({row["oat_c"] for row in rows}), oat, "OAT")
    lookup = {(row["pa_ft"], row["oat_c"]): row[field] for row in rows}
    q11, q12, q21, q22 = (lookup[(a, t)] for a, t in ((alt_low, temp_low), (alt_low, temp_high), (alt_high, temp_low), (alt_high, temp_high)))
    low = mix(pa, alt_low, alt_high, q11, q21)
    high = mix(pa, alt_low, alt_high, q12, q22)
    value = mix(oat, temp_low, temp_high, low, high)
    detail = dict(value=value, alt_low=alt_low, alt_high=alt_high, temp_low=temp_low, temp_high=temp_high,
                  q11=q11, q12=q12, q21=q21, q22=q22, low_temp_value=low, high_temp_value=high)
    return value, detail


def manual_distance(dataset, phase, weight, pa, oat, wind, grass):
    weight, pa, oat = (number(value, label) for value, label in ((weight, "Weight"), (pa, "Pressure altitude"), (oat, "OAT")))
    weights = sorted({row["weight_lb"] for row in dataset["rows"]})
    if weight <= 0 or weight > weights[-1]:
        raise ValueError(f"Weight must be positive and no greater than table maximum {weights[-1]:.1f} lb.")
    selected = next(value for value in weights if value >= weight)
    rows = [row for row in dataset["rows"] if row["weight_lb"] == selected]
    ground, ground_detail = grid_value(rows, "ground_ft", pa, oat)
    total, total_detail = grid_value(rows, "total_ft", pa, oat)
    steps = [source_step(dataset), dict(title="Weight table", formula="Use the next POH table not below actual weight", value=f"{weight:.1f} lb -> {selected:.1f} lb table"), *wind["steps"]]
    # Exact-axis lookups use a direct-cell step instead of a zero-denominator formula.
    for label, detail in (("Ground", ground_detail), ("50 ft", total_detail)):
        if detail["alt_low"] == detail["alt_high"] or detail["temp_low"] == detail["temp_high"]:
            low_math = linear_math(pa, detail["alt_low"], detail["alt_high"], detail["q11"], detail["q21"])
            high_math = linear_math(pa, detail["alt_low"], detail["alt_high"], detail["q12"], detail["q22"])
            temp_math = linear_math(oat, detail["temp_low"], detail["temp_high"], detail["low_temp_value"], detail["high_temp_value"])
            steps.append(dict(title=label + " POH lookup", formula="Altitude interpolation, then OAT interpolation; exact axes use their table values", value=(
                f"At OAT {detail['temp_low']:.1f}: {low_math}\nAt OAT {detail['temp_high']:.1f}: {high_math}\nOAT: {temp_math} ft")))
        else:
            steps.extend(interpolation_steps(label, detail, pa, oat))
    factor = 1.0
    for kind, speed in (("headwind", wind["headwind_kt"]), ("tailwind", wind["tailwind_kt"])):
        if speed > 1e-9:
            percent, knot_step, maximum = (dataset[kind + suffix] for suffix in ("_pct", "_step_kt", "_max_kt"))
            if percent is None or knot_step is None:
                raise ValueError(f"No {kind} correction rule recorded for this POH table.")
            if maximum is not None and speed > maximum:
                raise ValueError(f"{kind.capitalize()} exceeds recorded POH limit {maximum:.1f} kt.")
            sign = -1 if kind == "headwind" else 1
            factor = 1 + sign * percent / 100 * speed / knot_step
            steps.append(dict(title="Wind factor", formula="1 " + ("-" if sign < 0 else "+") + " (percent / 100) x (wind / knot step)", value=f"1 {'-' if sign < 0 else '+'} ({percent:.1f} / 100.0) x ({speed:.1f} / {knot_step:.1f}) = {factor * 100:.1f}%"))
    if factor <= 0:
        raise ValueError("Wind correction would produce a nonpositive distance.")
    corrected_ground, corrected_total = ground * factor, total * factor
    steps.append(dict(title="After wind", formula="POH distance x wind factor", value=f"Ground {ground:.1f} x {factor * 100:.1f}% = {corrected_ground:.1f} ft; 50 ft {total:.1f} x {factor * 100:.1f}% = {corrected_total:.1f} ft"))
    if grass:
        if dataset["grass_mode"] == "none":
            raise ValueError("No grass correction rule recorded for this POH table.")
        percent = dataset["grass_pct"] / 100
        ground_add = corrected_ground * percent
        total_add = ground_add if dataset["grass_mode"] == "ground_add" else corrected_total * percent
        total_basis = corrected_ground if dataset["grass_mode"] == "ground_add" else corrected_total
        steps.append(dict(title="Grass correction", formula="Add percentage of corrected ground roll to both distances" if dataset["grass_mode"] == "ground_add" else "Increase each corrected distance by percentage", value=(
            f"Ground: {corrected_ground:.1f} x {dataset['grass_pct']:.1f}% = +{ground_add:.1f}; {corrected_ground:.1f} + {ground_add:.1f} = {corrected_ground + ground_add:.1f} ft\n"
            f"50 ft: {total_basis:.1f} x {dataset['grass_pct']:.1f}% = +{total_add:.1f}; {corrected_total:.1f} + {total_add:.1f} = {corrected_total + total_add:.1f} ft")))
        corrected_ground += ground_add
        corrected_total += total_add
    result = dict(input_weight_lbs=weight, selected_table_lbs=selected, ground_roll_ft=corrected_ground,
                  headwind_component_kt=wind["headwind_kt"], tailwind_component_kt=wind["tailwind_kt"],
                  calculation_steps=steps)
    result["total_clear_50ft_ft" if phase == "takeoff" else "total_to_clear_50ft_ft"] = corrected_total
    for field in (("lift_off_kias", "at_50ft_kias") if phase == "takeoff" else ("at_50ft_kias",)):
        speed, detail = grid_value(rows, field, pa, oat)
        result[field] = speed
        steps.append(dict(title="POH speed - " + field, formula="Altitude interpolation, then OAT interpolation", value=(
            f"At OAT {detail['temp_low']:.1f}: " + linear_math(pa, detail["alt_low"], detail["alt_high"], detail["q11"], detail["q21"]) + "\n" +
            f"At OAT {detail['temp_high']:.1f}: " + linear_math(pa, detail["alt_low"], detail["alt_high"], detail["q12"], detail["q22"]) + "\nOAT: " +
            linear_math(oat, detail["temp_low"], detail["temp_high"], detail["low_temp_value"], detail["high_temp_value"]) + " KIAS")))
    if wind["crosswind_kt"] is not None:
        result["crosswind_component_kt"] = wind["crosswind_kt"]
    return result


def manual_cruise(dataset, altitude, low_alt, low_oat, high_alt, high_oat, rpm):
    altitude, low_alt, low_oat, high_alt, high_oat, rpm = [number(value, "Cruise input") for value in (altitude, low_alt, low_oat, high_alt, high_oat, rpm)]
    if low_alt > high_alt:
        low_alt, high_alt, low_oat, high_oat = high_alt, low_alt, high_oat, low_oat
    if low_alt == high_alt or not low_alt <= altitude <= high_alt:
        raise ValueError("Cruise pressure altitude must lie between two different OAT altitude points.")
    oat = mix(altitude, low_alt, high_alt, low_oat, high_oat)
    isa = isa_temp_c(altitude)
    offset = oat - isa
    steps = [source_step(dataset),
             dict(title="OAT interpolation", formula="Lower OAT + altitude ratio x OAT difference", value=f"{low_oat:.1f} + ({altitude:.1f} - {low_alt:.1f}) / ({high_alt:.1f} - {low_alt:.1f}) x ({high_oat:.1f} - {low_oat:.1f}) = {oat:.1f} C"),
             dict(title="ISA offset", formula="ISA = 15 - 2 x altitude / 1000; offset = OAT - ISA", value=f"ISA: 15.0 - 2.0 x {altitude / 1000:.1f} = {isa:.1f} C; offset: {oat:.1f} - ({isa:.1f}) = {offset:.1f} C")]
    fields = ("percent_bhp", "ktas", "gph")
    rows = dataset["rows"]
    altitudes = bracket(sorted({row["pa_ft"] for row in rows}), altitude, "Pressure altitude")
    values = []
    for alt in dict.fromkeys(altitudes):
        group = [row for row in rows if row["pa_ft"] == alt]
        temperatures = bracket(sorted({row["isa_offset_c"] for row in group}), offset, "ISA offset")
        temp_values, rpm_lines = [], []
        for temperature in dict.fromkeys(temperatures):
            cells = {row["rpm"]: row for row in group if row["isa_offset_c"] == temperature}
            low, high = bracket(sorted(cells), rpm, "RPM")
            interpolated = tuple(mix(rpm, low, high, cells[low][field], cells[high][field]) for field in fields)
            temp_values.append(interpolated)
            if low == high:
                rpm_lines.append(f"ISA {temperature:.1f}, exact RPM {rpm:.1f}: " + ", ".join(f"{field}={cells[low][field]:.1f}" for field in fields))
            else:
                rpm_lines.append(f"ISA {temperature:.1f}, RPM ratio=({rpm:.1f}-{low:.1f})/({high:.1f}-{low:.1f}): " + "; ".join(f"{field}: {cells[low][field]:.1f} + ratio x ({cells[high][field]:.1f}-{cells[low][field]:.1f}) = {value:.1f}" for field, value in zip(fields, interpolated)))
        low_values, high_values = temp_values[0], temp_values[-1]
        result = tuple(mix(offset, *temperatures, low, high) for low, high in zip(low_values, high_values))
        if temperatures[0] == temperatures[1]:
            temp_line = f"Exact ISA offset {offset:.1f}: " + ", ".join(f"{field}={value:.1f}" for field, value in zip(fields, result))
        else:
            temp_line = f"Temperature ratio=({offset:.1f}-{temperatures[0]:.1f})/({temperatures[1]:.1f}-{temperatures[0]:.1f}): " + "; ".join(f"{field}: {low:.1f} + ratio x ({high:.1f}-{low:.1f}) = {value:.1f}" for field, low, high, value in zip(fields, low_values, high_values, result))
        steps.append(dict(title=f"Cruise interpolation at {alt:.1f} ft", formula="RPM interpolation, then temperature interpolation", value="\n".join([*rpm_lines, temp_line])))
        values.append(result)
    low_values, high_values = values[0], values[-1]
    result = tuple(mix(altitude, *altitudes, low, high) for low, high in zip(low_values, high_values))
    if altitudes[0] == altitudes[1]:
        value = f"Exact altitude {altitude:.1f} ft: " + ", ".join(f"{field}={number:.1f}" for field, number in zip(fields, result))
    else:
        value = f"Altitude ratio=({altitude:.1f}-{altitudes[0]:.1f})/({altitudes[1]:.1f}-{altitudes[0]:.1f}): " + "; ".join(f"{field}: {low:.1f} + ratio x ({high:.1f}-{low:.1f}) = {number:.1f}" for field, low, high, number in zip(fields, low_values, high_values, result))
    steps.append(dict(title="Cruise result", formula=f"Reference weight {dataset['reference_weight_lb']:.1f} lb; altitude interpolation", value=value))
    return {"Pressure altitude ft": altitude, "OAT at altitude C": oat, "ISA temp at altitude C": isa,
            "Temp offset from ISA C": offset, "Percent BHP": result[0], "KTAS": result[1], "GPH": result[2], "calculation_steps": steps}
