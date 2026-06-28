# C172N Landing Distance Calculator
# POH Table: 2300 lb, flaps 40, power off, max braking
# Speed at 50 ft: 60 KIAS
# Paved, level, dry runway, zero wind baseline

import numpy as np

# pressure altitude ft
alts = np.array([0, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000], dtype=float)

# temperature C
temps = np.array([0, 10, 20, 30, 40], dtype=float)

# Ground roll table, ft
ground_roll = np.array([
    [495, 510, 530, 545, 565],
    [510, 530, 550, 565, 585],
    [530, 550, 570, 590, 610],
    [550, 570, 590, 610, 630],
    [570, 590, 615, 635, 655],
    [590, 615, 635, 655, 680],
    [615, 640, 660, 685, 705],
    [640, 660, 685, 710, 730],
    [665, 690, 710, 735, 760],
], dtype=float)

# Total distance to clear 50 ft obstacle, ft
total_50ft = np.array([
    [1205, 1235, 1265, 1295, 1330],
    [1235, 1265, 1300, 1330, 1365],
    [1265, 1300, 1335, 1370, 1405],
    [1300, 1335, 1370, 1405, 1440],
    [1335, 1370, 1410, 1445, 1480],
    [1370, 1410, 1450, 1485, 1525],
    [1415, 1455, 1490, 1535, 1570],
    [1455, 1495, 1535, 1575, 1615],
    [1500, 1540, 1580, 1620, 1665],
], dtype=float)


def interp_2d(pa, temp_c, table):
    """
    Bilinear interpolation from POH table.
    pa: pressure altitude ft
    temp_c: outside air temperature C
    table: ground_roll or total_50ft
    """

    pa = float(pa)
    temp_c = float(temp_c)

    if pa < alts[0] or pa > alts[-1]:
        raise ValueError("Pressure altitude out of table range: 0 to 8000 ft")

    if temp_c < temps[0] or temp_c > temps[-1]:
        raise ValueError("Temperature out of table range: 0 to 40 C")

    # interpolate along altitude for each temperature column
    values_at_temp_columns = []
    for j in range(len(temps)):
        values_at_temp_columns.append(np.interp(pa, alts, table[:, j]))

    # interpolate along temperature
    return float(np.interp(temp_c, temps, values_at_temp_columns))


def interp_2d_detail(pa, temp_c, table):
    value = interp_2d(pa, temp_c, table)

    i = np.searchsorted(alts, pa) - 1
    j = np.searchsorted(temps, temp_c) - 1

    i = np.clip(i, 0, len(alts)-2)
    j = np.clip(j, 0, len(temps)-2)

    x1, x2 = alts[i], alts[i+1]
    y1, y2 = temps[j], temps[j+1]

    q11 = table[i, j]
    q12 = table[i, j+1]
    q21 = table[i+1, j]
    q22 = table[i+1, j+1]

    low_temp_value = np.interp(pa, [x1, x2], [q11, q21])
    high_temp_value = np.interp(pa, [x1, x2], [q12, q22])

    return {
        "value": value,
        "alt_low": x1,
        "alt_high": x2,
        "temp_low": y1,
        "temp_high": y2,
        "q11": q11,
        "q12": q12,
        "q21": q21,
        "q22": q22,
        "low_temp_value": low_temp_value,
        "high_temp_value": high_temp_value,
    }


def interpolation_steps(label, detail, pa, temp_c):
    return [
        {
            "kind": "interpolation",
            "title": f"{label} POH interpolation",
            "label": label,
            "target_alt": f"{pa:.1f} ft",
            "target_temp": f"{temp_c:.1f} C",
            "alt_low": f"{detail['alt_low']:.1f} ft",
            "alt_high": f"{detail['alt_high']:.1f} ft",
            "temp_low": f"{detail['temp_low']:.1f} C",
            "temp_high": f"{detail['temp_high']:.1f} C",
            "q11": f"{detail['q11']:.1f} ft",
            "q21": f"{detail['q21']:.1f} ft",
            "q12": f"{detail['q12']:.1f} ft",
            "q22": f"{detail['q22']:.1f} ft",
            "low_formula": (
                f"{detail['q11']:.1f} + ({pa:.1f} - {detail['alt_low']:.1f}) / "
                f"({detail['alt_high']:.1f} - {detail['alt_low']:.1f}) x "
                f"({detail['q21']:.1f} - {detail['q11']:.1f})"
            ),
            "low_result": f"{detail['low_temp_value']:.1f} ft at {detail['temp_low']:.1f} C",
            "high_formula": (
                f"{detail['q12']:.1f} + ({pa:.1f} - {detail['alt_low']:.1f}) / "
                f"({detail['alt_high']:.1f} - {detail['alt_low']:.1f}) x "
                f"({detail['q22']:.1f} - {detail['q12']:.1f})"
            ),
            "high_result": f"{detail['high_temp_value']:.1f} ft at {detail['temp_high']:.1f} C",
            "temp_formula": (
                f"{detail['low_temp_value']:.1f} + ({temp_c:.1f} - {detail['temp_low']:.1f}) / "
                f"({detail['temp_high']:.1f} - {detail['temp_low']:.1f}) x "
                f"({detail['high_temp_value']:.1f} - {detail['low_temp_value']:.1f})"
            ),
            "value": f"{detail['value']:.1f} ft",
        },
    ]


def wind_correction_step(headwind_kt, tailwind_kt, factor):
    if headwind_kt > 0:
        formula = f"1 - 0.10 x ({headwind_kt:.1f} / 9.0)"
        value = f"{formula} = {factor * 100:.1f}%"
    elif tailwind_kt > 0:
        formula = f"1 + 0.10 x ({tailwind_kt:.1f} / 2.0)"
        value = f"{formula} = {factor * 100:.1f}%"
    else:
        value = "No wind correction: 100.0%"

    return {
        "title": "4. Wind factor",
        "formula": "POH wind correction factor",
        "value": value,
    }


def after_wind_step(base_gr, base_total, factor):
    return {
        "title": "5. After wind",
        "formula": "POH distance x wind factor",
        "value": (
            f"Ground: {base_gr:.1f} x {factor * 100:.1f}% = {base_gr * factor:.1f} ft; "
            f"50 ft: {base_total:.1f} x {factor * 100:.1f}% = {base_total * factor:.1f} ft"
        ),
    }


def grass_step(grass, wind_ground, grass_add):
    return {
        "title": "6. Grass add",
        "formula": "Grass = +45% of wind-corrected ground roll",
        "value": (
            f"0.45 x {wind_ground:.1f} = +{grass_add:.1f} ft"
            if grass else
            "Not used: +0 ft"
        ),
    }


def landing_distance(
    pressure_altitude_ft,
    oat_c,
    headwind_kt=0,
    tailwind_kt=0,
    crosswind_kt=None,
    wind_steps=None,
    grass=False
):
    """
    C172N landing distance calculator.

    headwind_kt: positive headwind component
    tailwind_kt: positive tailwind component
    grass: dry grass runway correction
    """

    wind_steps = wind_steps or []

    ground_detail = interp_2d_detail(pressure_altitude_ft, oat_c, ground_roll)
    total_detail = interp_2d_detail(pressure_altitude_ft, oat_c, total_50ft)
    base_gr = ground_detail["value"]
    base_total = total_detail["value"]
    gr = base_gr
    total = base_total
    factor = 1

    # Wind correction:
    # POH note:
    # decrease distances 10% for each 9 kt headwind
    # increase distances 10% for each 2 kt tailwind up to 10 kt
    if headwind_kt > 0 and tailwind_kt > 0:
        raise ValueError("Use either headwind or tailwind, not both.")

    if headwind_kt > 0:
        factor = 1 - 0.10 * (headwind_kt / 9)
        gr *= factor
        total *= factor

    if tailwind_kt > 0:
        if tailwind_kt > 10:
            raise ValueError("POH only allows tailwind correction up to 10 kt.")
        factor = 1 + 0.10 * (tailwind_kt / 2)
        gr *= factor
        total *= factor

    wind_ground = gr

    # Grass correction:
    # POH note: increase distances by 45% of ground roll figure.
    grass_add = 0
    if grass:
        grass_add = 0.45 * gr
        gr += grass_add
        total += grass_add

    result = {
        "headwind_component_kt": round(headwind_kt, 1),
        "tailwind_component_kt": round(tailwind_kt, 1),
        "ground_roll_ft": round(gr, 1),
        "total_to_clear_50ft_ft": round(total, 1),
        "calculation_steps": [
            {
                "title": "1. Inputs",
                "formula": "PA, OAT, wind, surface",
                "value": (
                    f"{pressure_altitude_ft:.1f} ft, {oat_c:.1f} C, "
                    f"HW {headwind_kt:.1f} kt, TW {tailwind_kt:.1f} kt"
                ),
            },
            *wind_steps,
            {
                "title": "2. POH conditions",
                "formula": "2300 lb, flaps 40, power off, max braking",
                "value": "Dry, level runway baseline",
            },
            {
                "title": "3. POH lookup",
                "formula": "Interpolate by PA and OAT",
                "value": f"Ground {base_gr:.1f} ft, 50 ft {base_total:.1f} ft",
            },
            *interpolation_steps("Ground", ground_detail, pressure_altitude_ft, oat_c),
            *interpolation_steps("50 ft", total_detail, pressure_altitude_ft, oat_c),
            wind_correction_step(headwind_kt, tailwind_kt, factor),
            after_wind_step(base_gr, base_total, factor),
            grass_step(grass, wind_ground, grass_add),
            {
                "title": "7. Final ground roll",
                "formula": "Wind-corrected ground + grass add",
                "value": f"{gr:.1f} ft",
            },
            {
                "title": "8. Final over 50 ft",
                "formula": "Wind-corrected 50 ft + grass add",
                "value": f"{total:.1f} ft",
            },
            {
                "title": "9. Approach speed",
                "formula": "POH speed at 50 ft",
                "value": "60.0 KIAS",
            },
        ],
    }

    if crosswind_kt is not None:
        result["crosswind_component_kt"] = round(crosswind_kt, 1)

    return result


# -------------------------
# Example
# -------------------------
if __name__ == "__main__":
    pa = float(input("Pressure altitude ft: "))
    oat = float(input("OAT C: "))
    hw = float(input("Headwind kt, enter 0 if none: "))
    tw = float(input("Tailwind kt, enter 0 if none: "))
    grass_input = input("Grass runway? y/n: ").lower().strip()
    grass = grass_input == "y"

    result = landing_distance(
        pressure_altitude_ft=pa,
        oat_c=oat,
        headwind_kt=hw,
        tailwind_kt=tw,
        grass=grass
    )

    print("\nC172N Landing Distance")
    print("---------------------")
    print(f"Ground roll: {result['ground_roll_ft']} ft")
    print(f"Total over 50 ft obstacle: {result['total_to_clear_50ft_ft']} ft")
