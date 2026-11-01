"""1974 C172M/Skyhawk reference, AAFC's N9850V scan, printed pp. 6-1 to 6-5.

This is NOT a verified, tail-specific FFCT flight manual.
Preserve this edition's values and provenance.
"""

from performance import grid_value, linear_math, mix, number
from cruise import bracket, isa_temp_c
from takeoff import interpolation_steps


MODE = "c172m1974"
SOURCE_URL = "https://airamericafc.com/wp-content/uploads/2024/03/N9850V-C172M-OM-1974.pdf"
MPH_PER_KNOT = 1852 / 1609.344
ALTITUDES = (0, 2500, 5000, 7500)
WINDS = (0, 10, 20)

# Rows within each matrix are 0/10/20 kt headwind; columns are ALTITUDES.
TAKEOFF = {
    2300: dict(speed_mph=68,
               ground=((865, 1040, 1255, 1565), (615, 750, 920, 1160), (405, 505, 630, 810)),
               total=((1525, 1910, 2480, 3855), (1170, 1485, 1955, 3110), (850, 1100, 1480, 2425))),
    2000: dict(speed_mph=63,
               ground=((630, 755, 905, 1120), (435, 530, 645, 810), (275, 340, 425, 595)),
               total=((1095, 1325, 1625, 2155), (820, 1005, 1250, 1685), (580, 720, 910, 1255))),
    1700: dict(speed_mph=58,
               ground=((435, 520, 625, 765), (290, 355, 430, 535), (175, 215, 270, 345)),
               total=((780, 920, 1095, 1370), (570, 680, 820, 1040), (385, 470, 575, 745))),
}
LANDING_GROUND = (520, 560, 605, 650)
LANDING_TOTAL = (1250, 1310, 1385, 1455)
# Figure 6-4: (RPM, percent BHP, TAS MPH, US gallons/hour), Skyhawk configuration.
CRUISE = {
    2500: ((2700, 87, 139, 9.6), (2600, 78, 133, 8.6), (2500, 70, 128, 7.7), (2400, 63, 122, 7.1), (2300, 57, 116, 6.6), (2200, 51, 109, 6.2)),
    5000: ((2700, 81, 138, 8.9), (2600, 73, 133, 8.1), (2500, 66, 128, 7.4), (2400, 60, 121, 6.8), (2300, 54, 114, 6.4), (2200, 48, 107, 6.0)),
    7500: ((2700, 76, 138, 8.4), (2600, 69, 133, 7.6), (2500, 63, 126, 7.1), (2400, 57, 119, 6.6), (2300, 51, 112, 6.2)),
    10000: ((2700, 72, 138, 7.9), (2600, 66, 131, 7.3), (2500, 59, 124, 6.8), (2400, 54, 117, 6.4), (2300, 48, 110, 6.0)),
    12500: ((2650, 65, 132, 7.2), (2500, 56, 122, 6.5), (2400, 51, 115, 6.2)),
}


def conditions(phase):
    return {
        "takeoff": "1974 reference only, not FFCT-confirmed; hard surface, flaps up; PA 0-7500 ft, headwind 0-20 kt; warm correction +10% per 25 F above ISA; dry grass adds 7% of total distance to BOTH distances; no tailwind rule.",
        "landing": "1974 reference only, not FFCT-confirmed; 2300 lb table; standard-day temperature only; 40-degree flaps, power off; approach IAS 70 MPH; headwind -10% per 5 kt; dry grass adds 20% of total distance to BOTH distances.",
        "cruise": "1974 SKYHAWK reference, not FFCT-confirmed; 2300 lb, standard-day temperature, lean mixture; McCauley 1C160/DTM7553 or CTM7553; normal cruise <=75% BHP. Standard Model 172 speeds are 1-3 MPH lower than this table.",
    }[phase]


def source_step(phase):
    figure = {"takeoff": "6-3", "landing": "6-5", "cruise": "6-4"}[phase]
    return dict(title="1974 reference source", formula=f"1974 Model 172 / Skyhawk Owner's Manual, Figure {figure}; AAFC N9850V scan", value=conditions(phase))


def table_view(phase):
    if phase == "takeoff":
        columns = ["Weight (lb)", "PA (ft)", "Headwind (kt)", "Ground (ft)", "Over 50 ft (ft)", "IAS at 50 ft (MPH)"]
        rows = [[weight, alt, wind, data["ground"][j][i], data["total"][j][i], data["speed_mph"]]
                for weight, data in sorted(TAKEOFF.items()) for j, wind in enumerate(WINDS) for i, alt in enumerate(ALTITUDES)]
    elif phase == "landing":
        columns = ["Table weight (lb)", "PA (ft)", "Standard OAT (C)", "Ground (ft)", "Over 50 ft (ft)", "Approach IAS (MPH)"]
        rows = [[2300, alt, isa_temp_c(alt), LANDING_GROUND[i], LANDING_TOTAL[i], 70] for i, alt in enumerate(ALTITUDES)]
    elif phase == "cruise":
        columns = ["PA (ft)", "RPM", "Power (% BHP)", "Skyhawk TAS (MPH)", "US gal/h"]
        rows = [[alt, *row] for alt, data in CRUISE.items() for row in data]
    else:
        raise ValueError("Unknown reference table.")
    return dict(columns=columns, rows=rows, source_url=SOURCE_URL, conditions=conditions(phase))


def lookup_steps(label, detail, pa, headwind):
    if detail["alt_low"] != detail["alt_high"] and detail["temp_low"] != detail["temp_high"]:
        step = interpolation_steps(label, detail, pa, headwind)[0]
        step.update(axis_label="PA / Headwind", second_axis_name="Headwind",
                    target_temp=f"{headwind:.1f} kt", temp_low=f"{detail['temp_low']:.1f} kt", temp_high=f"{detail['temp_high']:.1f} kt",
                    low_result=f"{detail['low_temp_value']:.1f} ft", high_result=f"{detail['high_temp_value']:.1f} ft")
        return step
    return dict(title=label + " reference lookup", formula="Altitude interpolation, then headwind interpolation", value=(
        "Lower wind: " + linear_math(pa, detail["alt_low"], detail["alt_high"], detail["q11"], detail["q21"]) + "\nHigher wind: " +
        linear_math(pa, detail["alt_low"], detail["alt_high"], detail["q12"], detail["q22"]) + "\nHeadwind: " +
        linear_math(headwind, detail["temp_low"], detail["temp_high"], detail["low_temp_value"], detail["high_temp_value"]) + " ft"))


def reference_distance(phase, weight, pa, oat, wind, grass):
    weight, pa, oat = [number(value, "Reference distance input") for value in (weight, pa, oat)]
    if not 0 < weight <= 2300:
        raise ValueError("1974 reference weight must be positive and no greater than 2300 lb.")
    if not 0 <= pa <= 7500:
        raise ValueError("1974 distance reference altitude range is 0-7500 ft.")
    if wind["tailwind_kt"] > 1e-9:
        raise ValueError("The selected 1974 reference provides no tailwind correction.")
    standard = isa_temp_c(pa)
    steps = [source_step(phase), *wind["steps"]]
    if phase == "takeoff":
        selected = next(value for value in sorted(TAKEOFF) if value >= weight)
        table = TAKEOFF[selected]
        if wind["headwind_kt"] > 20:
            raise ValueError("1974 takeoff reference headwind range is 0-20 kt.")
        cells = [dict(pa_ft=alt, oat_c=headwind, ground_ft=table["ground"][j][i], total_ft=table["total"][j][i])
                 for i, alt in enumerate(ALTITUDES) for j, headwind in enumerate(WINDS)]
        ground, detail = grid_value(cells, "ground_ft", pa, wind["headwind_kt"])
        total, total_detail = grid_value(cells, "total_ft", pa, wind["headwind_kt"])
        steps.extend([dict(title="Weight table", formula="Next POH weight table not below actual weight", value=f"{weight:.1f} -> {selected:.1f} lb"),
                      lookup_steps("Ground", detail, pa, wind["headwind_kt"]), lookup_steps("50 ft", total_detail, pa, wind["headwind_kt"])])
        delta_f = max(oat - standard, 0) * 1.8
        factor = 1 + .10 * delta_f / 25
        steps.append(dict(title="1974 warm-temperature correction", formula="ISA = 15 - 2 x PA/1000; +10% per 25 F ABOVE ISA; no cold-weather reduction", value=(
            f"ISA {standard:.1f} C; warm difference max({oat:.1f} - ({standard:.1f}), 0.0) x 1.8 = {delta_f:.1f} F\n"
            f"Factor = 1.0 + 0.1 x ({delta_f:.1f} / 25.0) = {factor * 100:.1f}%\n"
            f"Ground {ground:.1f} x {factor * 100:.1f}% = {ground * factor:.1f} ft; 50 ft {total:.1f} x {factor * 100:.1f}% = {total * factor:.1f} ft")))
        ground *= factor
        total *= factor
        speed = table["speed_mph"]
        grass_percent = .07
    elif phase == "landing":
        if abs(oat - standard) > .050000001:
            raise ValueError(f"1974 landing reference is standard-day only: OAT at {pa:.1f} ft must be {standard:.1f} C. No nonstandard-temperature correction is provided in Figure 6-5.")
        selected = 2300
        low, high = bracket(list(ALTITUDES), pa, "Pressure altitude")
        i, j = ALTITUDES.index(low), ALTITUDES.index(high)
        ground = mix(pa, low, high, LANDING_GROUND[i], LANDING_GROUND[j])
        total = mix(pa, low, high, LANDING_TOTAL[i], LANDING_TOTAL[j])
        steps.append(dict(title="Landing altitude interpolation", formula="2300 lb standard-day reference table", value="Ground: " + linear_math(pa, low, high, LANDING_GROUND[i], LANDING_GROUND[j]) + " ft\n50 ft: " + linear_math(pa, low, high, LANDING_TOTAL[i], LANDING_TOTAL[j]) + " ft"))
        factor = 1 - .10 * wind["headwind_kt"] / 5
        if factor <= 0:
            raise ValueError("1974 landing wind correction would give a nonpositive distance.")
        steps.append(dict(title="1974 landing headwind correction", formula="Reduce both distances 10% for each 5 kt headwind", value=f"1.0 - 0.1 x ({wind['headwind_kt']:.1f} / 5.0) = {factor * 100:.1f}%\nGround {ground:.1f} x {factor * 100:.1f}% = {ground * factor:.1f} ft; 50 ft {total:.1f} x {factor * 100:.1f}% = {total * factor:.1f} ft"))
        ground *= factor
        total *= factor
        speed = 70
        grass_percent = .20
    else:
        raise ValueError("Unknown reference distance phase.")
    if grass:
        add = total * grass_percent
        steps.append(dict(title="1974 dry-grass correction", formula="Add a percentage of TOTAL over-50-ft distance to BOTH distances", value=f"{total:.1f} x {grass_percent * 100:.1f}% = +{add:.1f} ft\nGround: {ground:.1f} + {add:.1f} = {ground + add:.1f} ft; 50 ft: {total:.1f} + {add:.1f} = {total + add:.1f} ft"))
        ground += add
        total += add
    steps.append(dict(title="IAS unit conversion", formula="knots = MPH / 1.150779448", value=f"{speed:.1f} MPH / 1.150779448 = {speed / MPH_PER_KNOT:.1f} KIAS"))
    result = dict(input_weight_lbs=weight, selected_table_lbs=selected, ground_roll_ft=ground,
                  headwind_component_kt=wind["headwind_kt"], tailwind_component_kt=wind["tailwind_kt"],
                  calculation_steps=steps)
    result["total_clear_50ft_ft" if phase == "takeoff" else "total_to_clear_50ft_ft"] = total
    result["at_50ft_kias" if phase == "takeoff" else "approach_kias"] = speed / MPH_PER_KNOT
    if wind["crosswind_kt"] is not None:
        result["crosswind_component_kt"] = wind["crosswind_kt"]
    return result


def reference_cruise(alt, low_alt, low_oat, high_alt, high_oat, rpm):
    alt, low_alt, low_oat, high_alt, high_oat, rpm = [number(value, "Reference cruise input") for value in (alt, low_alt, low_oat, high_alt, high_oat, rpm)]
    if low_alt > high_alt:
        low_alt, high_alt, low_oat, high_oat = high_alt, low_alt, high_oat, low_oat
    if low_alt == high_alt or not low_alt <= alt <= high_alt:
        raise ValueError("Cruise altitude must be between two different OAT altitude points.")
    oat = mix(alt, low_alt, high_alt, low_oat, high_oat)
    standard = isa_temp_c(alt)
    if abs(oat - standard) > .050000001:
        raise ValueError(f"1974 cruise reference is standard-day only: interpolated OAT must be {standard:.1f} C at {alt:.1f} ft. Nonstandard-temperature values need the aircraft's Power Computer or matching supplement.")
    low, high = bracket(sorted(CRUISE), alt, "Pressure altitude")
    steps = [source_step("cruise"), dict(title="OAT and standard-day check", formula="OAT interpolation; ISA = 15 - 2 x PA/1000", value=linear_math(alt, low_alt, high_alt, low_oat, high_oat) + f" C; ISA {standard:.1f} C")]
    values = []
    for altitude in dict.fromkeys((low, high)):
        cells = {row[0]: row[1:] for row in CRUISE[altitude]}
        r0, r1 = bracket(sorted(cells), rpm, "RPM")
        interpolated = tuple(mix(rpm, r0, r1, a, b) for a, b in zip(cells[r0], cells[r1]))
        steps.append(dict(title=f"1974 cruise RPM at {altitude:.1f} ft", formula="Interpolate power, TAS in MPH, and fuel flow", value="\n".join(label + ": " + linear_math(rpm, r0, r1, a, b) for label, a, b in zip(("% BHP", "TAS MPH", "US gal/h"), cells[r0], cells[r1]))))
        values.append(interpolated)
    result = tuple(mix(alt, low, high, a, b) for a, b in zip(values[0], values[-1]))
    if result[0] > 75 + 1e-9:
        raise ValueError("This RPM gives more than the 1974 reference's normal 75% cruise power limit.")
    steps.append(dict(title="1974 cruise altitude interpolation", formula="Interpolate between pressure-altitude tables", value="\n".join(label + ": " + linear_math(alt, low, high, a, b) for label, a, b in zip(("% BHP", "TAS MPH", "US gal/h"), values[0], values[-1]))))
    steps.append(dict(title="TAS unit conversion", formula="KTAS = TAS MPH / 1.150779448", value=f"{result[1]:.1f} MPH / 1.150779448 = {result[1] / MPH_PER_KNOT:.1f} KTAS"))
    return {"Pressure altitude ft": alt, "OAT at altitude C": oat, "ISA temp at altitude C": standard,
            "Temp offset from ISA C": oat - standard, "Percent BHP": result[0],
            "KTAS": result[1] / MPH_PER_KNOT, "GPH": result[2], "calculation_steps": steps}
