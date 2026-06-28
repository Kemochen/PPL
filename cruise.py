# C172N Cruise Performance Calculator
# Conditions: 2300 lb, recommended lean mixture
#
# Input:
#   Pressure altitude ft
#   Sea level / 0 ft OAT °C
#   RPM
#
# Output:
#   %BHP, KTAS, GPH
#
# Method:
#   Manual POH-style table interpolation only.
#   No weighted prediction.
#   No extrapolation outside table range.

# data[(pressure_altitude_ft, rpm, temp_offset_from_ISA_C)] = (%BHP, KTAS, GPH)
#
# temp_offset:
#   -20 = 20°C below standard
#     0 = standard temperature
#   +20 = 20°C above standard

data = {
    # 2000 ft
    (2000, 2400, -20): (72, 111, 8.0),
    (2000, 2300, -20): (64, 106, 7.1),
    (2000, 2200, -20): (56, 101, 6.3),
    (2000, 2100, -20): (50, 95, 5.8),

    (2000, 2500, 0): (75, 116, 8.4),
    (2000, 2400, 0): (67, 111, 7.5),
    (2000, 2300, 0): (60, 105, 6.7),
    (2000, 2200, 0): (53, 100, 6.1),
    (2000, 2100, 0): (47, 94, 5.6),

    (2000, 2500, 20): (71, 115, 7.9),
    (2000, 2400, 20): (63, 110, 7.1),
    (2000, 2300, 20): (56, 105, 6.3),
    (2000, 2200, 20): (50, 99, 5.8),
    (2000, 2100, 20): (45, 93, 5.4),

    # 4000 ft
    (4000, 2500, -20): (76, 116, 8.5),
    (4000, 2400, -20): (68, 111, 7.6),
    (4000, 2300, -20): (60, 105, 6.8),
    (4000, 2200, -20): (54, 100, 6.1),
    (4000, 2100, -20): (48, 94, 5.6),

    (4000, 2550, 0): (75, 118, 8.4),
    (4000, 2500, 0): (71, 115, 8.0),
    (4000, 2400, 0): (64, 110, 7.1),
    (4000, 2300, 0): (57, 105, 6.4),
    (4000, 2200, 0): (51, 99, 5.9),
    (4000, 2100, 0): (46, 93, 5.5),

    (4000, 2550, 20): (71, 118, 7.9),
    (4000, 2500, 20): (67, 115, 7.5),
    (4000, 2400, 20): (60, 109, 6.7),
    (4000, 2300, 20): (54, 104, 6.1),
    (4000, 2200, 20): (48, 98, 5.7),
    (4000, 2100, 20): (44, 92, 5.3),

    # 6000 ft
    (6000, 2500, -20): (72, 116, 8.1),
    (6000, 2400, -20): (64, 110, 7.2),
    (6000, 2300, -20): (57, 105, 6.5),
    (6000, 2200, -20): (51, 99, 5.9),
    (6000, 2100, -20): (46, 93, 5.5),

    (6000, 2600, 0): (75, 120, 8.4),
    (6000, 2500, 0): (67, 115, 7.6),
    (6000, 2400, 0): (60, 109, 6.8),
    (6000, 2300, 0): (54, 104, 6.2),
    (6000, 2200, 0): (49, 98, 5.7),
    (6000, 2100, 0): (44, 92, 5.4),

    (6000, 2600, 20): (71, 120, 7.9),
    (6000, 2500, 20): (64, 114, 7.1),
    (6000, 2400, 20): (57, 109, 6.4),
    (6000, 2300, 20): (52, 103, 5.9),
    (6000, 2200, 20): (47, 97, 5.5),
    (6000, 2100, 20): (42, 91, 5.2),

    # 8000 ft
    (8000, 2600, -20): (76, 120, 8.6),
    (8000, 2500, -20): (68, 115, 7.7),
    (8000, 2400, -20): (61, 110, 6.9),
    (8000, 2300, -20): (55, 104, 6.2),
    (8000, 2200, -20): (49, 98, 5.7),

    (8000, 2650, 0): (75, 122, 8.4),
    (8000, 2600, 0): (71, 120, 8.0),
    (8000, 2500, 0): (64, 114, 7.2),
    (8000, 2400, 0): (58, 109, 6.5),
    (8000, 2300, 0): (52, 103, 6.0),
    (8000, 2200, 0): (47, 97, 5.5),

    (8000, 2650, 20): (71, 122, 7.9),
    (8000, 2600, 20): (67, 119, 7.5),
    (8000, 2500, 20): (60, 113, 6.8),
    (8000, 2400, 20): (55, 108, 6.2),
    (8000, 2300, 20): (50, 102, 5.8),
    (8000, 2200, 20): (45, 96, 5.4),

    # 10000 ft
    (10000, 2650, -20): (76, 122, 8.5),
    (10000, 2600, -20): (72, 120, 8.1),
    (10000, 2500, -20): (65, 114, 7.3),
    (10000, 2400, -20): (58, 109, 6.5),
    (10000, 2300, -20): (52, 103, 6.0),
    (10000, 2200, -20): (47, 97, 5.6),

    (10000, 2650, 0): (71, 122, 8.0),
    (10000, 2600, 0): (68, 119, 7.6),
    (10000, 2500, 0): (61, 114, 6.8),
    (10000, 2400, 0): (55, 108, 6.2),
    (10000, 2300, 0): (50, 102, 5.8),
    (10000, 2200, 0): (45, 96, 5.4),

    (10000, 2650, 20): (67, 121, 7.5),
    (10000, 2600, 20): (64, 118, 7.1),
    (10000, 2500, 20): (58, 112, 6.5),
    (10000, 2400, 20): (52, 107, 6.0),
    (10000, 2300, 20): (48, 101, 5.6),
    (10000, 2200, 20): (44, 95, 5.3),

    # 12000 ft
    (12000, 2600, -20): (68, 119, 7.7),
    (12000, 2500, -20): (62, 114, 6.9),
    (12000, 2400, -20): (56, 108, 6.3),
    (12000, 2300, -20): (50, 102, 5.8),
    (12000, 2200, -20): (46, 96, 5.5),

    (12000, 2600, 0): (64, 118, 7.2),
    (12000, 2500, 0): (58, 113, 6.5),
    (12000, 2400, 0): (53, 107, 6.0),
    (12000, 2300, 0): (48, 101, 5.6),
    (12000, 2200, 0): (44, 95, 5.4),

    (12000, 2600, 20): (61, 117, 6.8),
    (12000, 2500, 20): (55, 111, 6.2),
    (12000, 2400, 20): (51, 106, 5.8),
    (12000, 2300, 20): (46, 100, 5.5),
    (12000, 2200, 20): (43, 94, 5.3),
}


def isa_temp_c(alt_ft):
    """
    ISA temperature at altitude.
    Approximation used by many POH tables:
    Sea level ISA = 15°C
    Lapse rate = 2°C per 1000 ft
    """
    return 15 - 2 * (alt_ft / 1000)


def lerp(x, x0, y0, x1, y1):
    """
    Linear interpolation.
    """
    if x1 == x0:
        return y0
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)


def lerp_tuple(x, x0, v0, x1, v1):
    """
    Linear interpolation for tuple:
    (%BHP, KTAS, GPH)
    """
    return tuple(
        lerp(x, x0, v0[i], x1, v1[i])
        for i in range(3)
    )


def bracket(sorted_values, x, label="value"):
    """
    Find the two nearest table values surrounding x.

    If x exactly equals a table value:
        return x, x

    Otherwise:
        return lower, upper

    No extrapolation allowed.
    """
    sorted_values = sorted(sorted_values)

    if x < sorted_values[0] or x > sorted_values[-1]:
        raise ValueError(
            f"{label} {x} is outside table range "
            f"{sorted_values[0]} to {sorted_values[-1]}."
        )

    for v in sorted_values:
        if x == v:
            return v, v

    lower = max(v for v in sorted_values if v < x)
    upper = min(v for v in sorted_values if v > x)

    return lower, upper


def get_exact_table_value(alt, temp_offset, rpm):
    """
    Get exact POH table cell.
    Return None if the cell is missing.
    """
    return data.get((alt, rpm, temp_offset), None)


def interpolate_rpm_at_fixed_alt_temp(alt, temp_offset, rpm):
    """
    Fixed altitude + fixed temperature block.

    Example:
        6000 ft, standard temp block, interpolate between
        2300 RPM and 2400 RPM.

    This uses only the nearest RPM rows in that specific block.
    """
    available_rpms = sorted(
        r for (a, r, t) in data.keys()
        if a == alt and t == temp_offset
    )

    if not available_rpms:
        return None

    try:
        rpm_low, rpm_high = bracket(available_rpms, rpm, label="RPM")
    except ValueError:
        return None

    v_low = get_exact_table_value(alt, temp_offset, rpm_low)
    v_high = get_exact_table_value(alt, temp_offset, rpm_high)

    if v_low is None or v_high is None:
        return None

    if rpm_low == rpm_high:
        return v_low

    return lerp_tuple(rpm, rpm_low, v_low, rpm_high, v_high)


def interpolate_temp_at_fixed_alt(alt, temp_offset, rpm):
    """
    Fixed altitude.

    Steps:
    1. Find lower and upper temperature blocks:
       -20, 0, +20
    2. Inside each temperature block, interpolate by RPM
    3. Interpolate between temperature blocks
    """
    temp_blocks = sorted(
        set(t for (a, r, t) in data.keys() if a == alt)
    )

    try:
        temp_low, temp_high = bracket(
            temp_blocks,
            temp_offset,
            label="temperature offset from ISA"
        )
    except ValueError:
        return None

    v_low = interpolate_rpm_at_fixed_alt_temp(
        alt,
        temp_low,
        rpm
    )

    v_high = interpolate_rpm_at_fixed_alt_temp(
        alt,
        temp_high,
        rpm
    )

    if v_low is None or v_high is None:
        return None

    if temp_low == temp_high:
        return v_low

    return lerp_tuple(
        temp_offset,
        temp_low,
        v_low,
        temp_high,
        v_high
    )


def format_cruise_tuple(values):
    return f"{values[0]:.1f}%, {values[1]:.1f} KTAS, {values[2]:.1f} GPH"


def format_temp_offset(value):
    return f"{value:+.1f} C"


def interpolate_rpm_detail(alt, temp_offset, rpm):
    available_rpms = sorted(
        r for (a, r, t) in data.keys()
        if a == alt and t == temp_offset
    )

    if not available_rpms:
        return None, []

    try:
        rpm_low, rpm_high = bracket(available_rpms, rpm, label="RPM")
    except ValueError:
        return None, []

    v_low = get_exact_table_value(alt, temp_offset, rpm_low)
    v_high = get_exact_table_value(alt, temp_offset, rpm_high)

    if v_low is None or v_high is None:
        return None, []

    if rpm_low == rpm_high:
        result = v_low
        value = f"Exact {rpm:.1f} RPM row = {format_cruise_tuple(result)}"
    else:
        result = lerp_tuple(rpm, rpm_low, v_low, rpm_high, v_high)
        value = (
            f"{rpm_low:.1f} RPM: {format_cruise_tuple(v_low)}; "
            f"{rpm_high:.1f} RPM: {format_cruise_tuple(v_high)}; "
            f"{rpm:.1f} RPM result = {format_cruise_tuple(result)}"
        )

    return result, [{
        "title": f"RPM bracket at {alt:.0f} ft / ISA {format_temp_offset(temp_offset)}",
        "formula": "Interpolate between nearest RPM rows",
        "value": value,
    }]


def interpolate_temp_detail(alt, temp_offset, rpm):
    temp_blocks = sorted(
        set(t for (a, r, t) in data.keys() if a == alt)
    )

    try:
        temp_low, temp_high = bracket(
            temp_blocks,
            temp_offset,
            label="temperature offset from ISA"
        )
    except ValueError:
        return None, []

    v_low, low_steps = interpolate_rpm_detail(alt, temp_low, rpm)
    if temp_low == temp_high:
        v_high, high_steps = v_low, []
    else:
        v_high, high_steps = interpolate_rpm_detail(alt, temp_high, rpm)

    if v_low is None or v_high is None:
        return None, []

    steps = []

    if temp_low == temp_high:
        result = v_low
        value = f"Exact ISA offset {format_temp_offset(temp_offset)} = {format_cruise_tuple(result)}"
    else:
        result = lerp_tuple(temp_offset, temp_low, v_low, temp_high, v_high)
        value = (
            f"{format_temp_offset(temp_low)}: {format_cruise_tuple(v_low)}; "
            f"{format_temp_offset(temp_high)}: {format_cruise_tuple(v_high)}; "
            f"{format_temp_offset(temp_offset)} result = {format_cruise_tuple(result)}"
        )

    steps.append({
        "title": f"Temperature bracket at {alt:.0f} ft",
        "formula": "Interpolate between ISA temperature offset blocks",
        "value": value,
    })

    return result, steps


def estimate_from_oat_at_altitude_detail(alt_ft, oat_at_altitude_c, rpm):
    isa = isa_temp_c(alt_ft)
    temp_offset = oat_at_altitude_c - isa

    altitudes = sorted(set(a for (a, r, t) in data.keys()))
    alt_low, alt_high = bracket(
        altitudes,
        alt_ft,
        label="pressure altitude"
    )

    v_low, low_steps = interpolate_temp_detail(alt_low, temp_offset, rpm)
    v_high, high_steps = interpolate_temp_detail(alt_high, temp_offset, rpm)

    if v_low is None or v_high is None:
        raise ValueError(
            "This pressure altitude / temperature / RPM combination "
            "cannot be interpolated because one or more required POH "
            "table cells are missing.\n"
            "Try a lower RPM, or check whether this point is inside the "
            "available POH table area."
        )

    steps = []
    steps.extend(low_steps)
    if alt_high != alt_low:
        steps.extend(high_steps)

    if alt_low == alt_high:
        result = v_low
        altitude_value = f"Exact altitude {alt_ft:.1f} ft = {format_cruise_tuple(result)}"
    else:
        result = lerp_tuple(alt_ft, alt_low, v_low, alt_high, v_high)
        altitude_value = (
            f"{alt_low:.1f} ft: {format_cruise_tuple(v_low)}; "
            f"{alt_high:.1f} ft: {format_cruise_tuple(v_high)}; "
            f"{alt_ft:.1f} ft result = {format_cruise_tuple(result)}"
        )

    steps.append({
        "title": "Final altitude interpolation",
        "formula": "Interpolate between pressure-altitude rows",
        "value": altitude_value,
    })

    return {
        "Pressure altitude ft": round(alt_ft, 1),
        "ISA temp at altitude C": round(isa, 1),
        "OAT at altitude C": round(oat_at_altitude_c, 1),
        "Temp offset from ISA C": round(temp_offset, 1),
        "Percent BHP": round(result[0], 1),
        "KTAS": round(result[1], 1),
        "GPH": round(result[2], 1),
    }, steps


def estimate_from_oat_at_altitude(alt_ft, oat_at_altitude_c, rpm):
    """
    Main POH-style interpolation.

    Inputs:
        alt_ft:
            Pressure altitude in feet.

        oat_at_altitude_c:
            Outside air temperature at cruise altitude.

        rpm:
            Cruise RPM.

    Returns:
        dict with BHP, KTAS, GPH.

    Logic:
        1. Convert OAT to temperature offset from ISA.
        2. Find nearest lower and upper altitude blocks.
        3. At each altitude block:
            a. interpolate by RPM
            b. interpolate by temperature
        4. Interpolate between altitude blocks.
    """
    isa = isa_temp_c(alt_ft)
    temp_offset = oat_at_altitude_c - isa

    altitudes = sorted(set(a for (a, r, t) in data.keys()))

    alt_low, alt_high = bracket(
        altitudes,
        alt_ft,
        label="pressure altitude"
    )

    v_low = interpolate_temp_at_fixed_alt(
        alt_low,
        temp_offset,
        rpm
    )

    v_high = interpolate_temp_at_fixed_alt(
        alt_high,
        temp_offset,
        rpm
    )

    if v_low is None or v_high is None:
        raise ValueError(
            "This pressure altitude / temperature / RPM combination "
            "cannot be interpolated because one or more required POH "
            "table cells are missing.\n"
            "Try a lower RPM, or check whether this point is inside the "
            "available POH table area."
        )

    if alt_low == alt_high:
        result = v_low
    else:
        result = lerp_tuple(
            alt_ft,
            alt_low,
            v_low,
            alt_high,
            v_high
        )

    return {
        "Pressure altitude ft": round(alt_ft, 1),
        "ISA temp at altitude C": round(isa, 1),
        "OAT at altitude C": round(oat_at_altitude_c, 1),
        "Temp offset from ISA C": round(temp_offset, 1),
        "Percent BHP": round(result[0], 1),
        "KTAS": round(result[1], 1),
        "GPH": round(result[2], 1),
    }


def estimate_from_oat_bracket(
    alt_ft,
    lower_alt_ft,
    lower_oat_c,
    upper_alt_ft,
    upper_oat_c,
    rpm
):
    if lower_alt_ft == upper_alt_ft:
        raise ValueError("Lower and upper OAT altitudes must be different.")

    if lower_alt_ft > upper_alt_ft:
        lower_alt_ft, upper_alt_ft = upper_alt_ft, lower_alt_ft
        lower_oat_c, upper_oat_c = upper_oat_c, lower_oat_c

    if alt_ft < lower_alt_ft or alt_ft > upper_alt_ft:
        raise ValueError("Pressure altitude must be between the two OAT altitude points.")

    oat_altitude = lerp(
        alt_ft,
        lower_alt_ft,
        lower_oat_c,
        upper_alt_ft,
        upper_oat_c
    )

    result, interpolation_steps = estimate_from_oat_at_altitude_detail(
        alt_ft,
        oat_altitude,
        rpm
    )

    result["calculation_steps"] = [
        {
            "title": "1. Inputs",
            "formula": "PA, OAT bracket, RPM",
            "value": (
                f"PA {alt_ft:.1f} ft, "
                f"{lower_alt_ft:.1f} ft OAT {lower_oat_c:.1f} C, "
                f"{upper_alt_ft:.1f} ft OAT {upper_oat_c:.1f} C, "
                f"{rpm:.1f} RPM"
            ),
        },
        {
            "title": "2. OAT interpolation",
            "formula": "OAT = lower OAT + altitude ratio x OAT difference",
            "value": (
                f"{lower_oat_c:.1f} + ({alt_ft:.1f} - {lower_alt_ft:.1f}) / "
                f"({upper_alt_ft:.1f} - {lower_alt_ft:.1f}) x "
                f"({upper_oat_c:.1f} - {lower_oat_c:.1f}) = {oat_altitude:.1f} C"
            ),
        },
        {
            "title": "3. ISA temperature",
            "formula": "15 C - 2 C per 1000 ft",
            "value": f"15.0 - 2.0 x {alt_ft / 1000:.1f} = {result['ISA temp at altitude C']:.1f} C",
        },
        {
            "title": "4. ISA offset",
            "formula": "OAT at altitude - ISA temp",
            "value": f"{oat_altitude:.1f} - {result['ISA temp at altitude C']:.1f} = {result['Temp offset from ISA C']:.1f} C",
        },
        *interpolation_steps,
    ]

    return result


def main():
    print("C172N Cruise Performance Calculator")
    print("2300 lb, recommended lean mixture")
    print("-----------------------------------")
    print("Input two OAT altitude points.")
    print("Program interpolates OAT at cruise altitude.")
    print()

    try:
        altitude = float(input("Pressure altitude ft: "))
        lower_altitude = float(input("Lower OAT altitude ft: "))
        lower_oat = float(input("Lower altitude OAT C: "))
        upper_altitude = float(input("Upper OAT altitude ft: "))
        upper_oat = float(input("Upper altitude OAT C: "))
        rpm = float(input("RPM: "))

        result = estimate_from_oat_bracket(
            alt_ft=altitude,
            lower_alt_ft=lower_altitude,
            lower_oat_c=lower_oat,
            upper_alt_ft=upper_altitude,
            upper_oat_c=upper_oat,
            rpm=rpm,
        )

        print("\nEstimated cruise performance:")
        print("-----------------------------------")
        for key, value in result.items():
            print(f"{key}: {value}")

    except ValueError as e:
        print("\nError:")
        print(e)

    except Exception as e:
        print("\nUnexpected error:")
        print(e)


if __name__ == "__main__":
    main()
