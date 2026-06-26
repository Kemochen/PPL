import numpy as np

alts = np.array([0,1000,2000,3000,4000,5000,6000,7000,8000], dtype=float)
temps = np.array([0,10,20,30,40], dtype=float)

tables = {
    2300: {
        "lift_off": 52,
        "at_50ft": 59,
        "ground": np.array([
            [720,790,865,950,1045,1150,1265,1400,1550],
            [775,850,930,1025,1125,1240,1365,1510,1675],
            [835,915,1000,1100,1210,1335,1475,1630,1805],
            [895,980,1075,1185,1300,1435,1585,1755,1945],
            [960,1050,1155,1270,1400,1540,1705,1890,2095],
        ], dtype=float).T,
        "total": np.array([
            [1300,1420,1555,1710,1880,2075,2305,2565,2870],
            [1390,1525,1670,1835,2025,2240,2485,2770,3110],
            [1490,1630,1790,1970,2175,2410,2680,3000,3375],
            [1590,1745,1915,2115,2335,2595,2895,3245,3670],
            [1700,1865,2050,2265,2510,2790,3125,3515,3990],
        ], dtype=float).T,
    },

    2100: {
        "lift_off": 50,
        "at_50ft": 56,
        "ground": np.array([
            [585,640,700,770,845,930,1020,1130,1245],
            [630,690,755,830,910,1000,1100,1215,1345],
            [680,740,810,890,980,1075,1185,1310,1450],
            [725,790,870,955,1050,1155,1270,1410,1560],
            [780,850,935,1025,1130,1240,1370,1515,1680],
        ], dtype=float).T,
        "total": np.array([
            [1070,1165,1270,1390,1525,1680,1855,2050,2275],
            [1140,1245,1360,1490,1640,1805,1995,2210,2460],
            [1220,1330,1455,1595,1755,1935,2140,2380,2655],
            [1300,1420,1555,1710,1880,2075,2305,2560,2865],
            [1390,1520,1665,1830,2015,2230,2475,2755,3090],
        ], dtype=float).T,
    },

    1900: {
        "lift_off": 47,
        "at_50ft": 54,
        "ground": np.array([
            [470,515,560,615,670,740,810,895,985],
            [505,550,605,660,725,795,875,965,1065],
            [540,590,645,710,780,855,940,1035,1145],
            [580,635,695,760,835,920,1010,1115,1230],
            [620,680,745,815,895,985,1085,1195,1320],
        ], dtype=float).T,
        "total": np.array([
            [865,940,1025,1115,1220,1340,1470,1620,1790],
            [920,1005,1095,1195,1305,1435,1575,1740,1925],
            [985,1070,1170,1275,1400,1535,1690,1865,2065],
            [1045,1140,1245,1365,1495,1640,1810,2000,2220],
            [1115,1215,1323,1455,1595,1755,1940,2145,2385],
        ], dtype=float).T,
    },
}


def select_weight_table(weight_lbs):
    if weight_lbs <= 1900:
        return 1900
    elif weight_lbs <= 2100:
        return 2100
    elif weight_lbs <= 2300:
        return 2300
    else:
        raise ValueError("Weight exceeds POH table maximum 2300 lb")


def interp_2d(pa_ft, temp_c, table):
    if not alts[0] <= pa_ft <= alts[-1]:
        raise ValueError("Pressure altitude out of table range")
    if not temps[0] <= temp_c <= temps[-1]:
        raise ValueError("Temperature out of table range")

    i = np.searchsorted(alts, pa_ft) - 1
    j = np.searchsorted(temps, temp_c) - 1

    i = np.clip(i, 0, len(alts)-2)
    j = np.clip(j, 0, len(temps)-2)

    x1, x2 = alts[i], alts[i+1]
    y1, y2 = temps[j], temps[j+1]

    q11 = table[i, j]
    q12 = table[i, j+1]
    q21 = table[i+1, j]
    q22 = table[i+1, j+1]

    tx = (pa_ft - x1) / (x2 - x1)
    ty = (temp_c - y1) / (y2 - y1)

    return (
        q11 * (1-tx) * (1-ty)
        + q21 * tx * (1-ty)
        + q12 * (1-tx) * ty
        + q22 * tx * ty
    )


def wind_correction(distance, headwind_kt=0, tailwind_kt=0):
    if headwind_kt > 0 and tailwind_kt > 0:
        raise ValueError("Use headwind or tailwind, not both")

    if headwind_kt > 0:
        return distance * (1 - 0.10 * headwind_kt / 9)
    if tailwind_kt > 0:
        return distance * (1 + 0.10 * tailwind_kt / 2)

    return distance


def takeoff_distance(weight_lbs, pressure_altitude_ft, oat_c,
                     headwind_kt=0, tailwind_kt=0, grass=False):

    selected_weight = select_weight_table(weight_lbs)
    data = tables[selected_weight]

    ground = interp_2d(pressure_altitude_ft, oat_c, data["ground"])
    total = interp_2d(pressure_altitude_ft, oat_c, data["total"])

    ground = wind_correction(ground, headwind_kt, tailwind_kt)
    total = wind_correction(total, headwind_kt, tailwind_kt)

    if grass:
        add = ground * 0.15
        ground += add
        total += add

    return {
        "input_weight_lbs": weight_lbs,
        "selected_table_lbs": selected_weight,
        "ground_roll_ft": round(ground),
        "total_clear_50ft_ft": round(total),
        "lift_off_kias": data["lift_off"],
        "at_50ft_kias": data["at_50ft"],
    }


# Example
print(takeoff_distance(
    weight_lbs=2000,
    pressure_altitude_ft=2500,
    oat_c=15,
    headwind_kt=0,
    tailwind_kt=0,
    grass=False
))