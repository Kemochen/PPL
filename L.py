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


def landing_distance(
    pressure_altitude_ft,
    oat_c,
    headwind_kt=0,
    tailwind_kt=0,
    grass=False
):
    """
    C172N landing distance calculator.

    headwind_kt: positive headwind component
    tailwind_kt: positive tailwind component
    grass: dry grass runway correction
    """

    gr = interp_2d(pressure_altitude_ft, oat_c, ground_roll)
    total = interp_2d(pressure_altitude_ft, oat_c, total_50ft)

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

    # Grass correction:
    # POH note: increase distances by 45% of ground roll figure.
    if grass:
        grass_add = 0.45 * gr
        gr += grass_add
        total += grass_add

    return {
        "ground_roll_ft": round(gr),
        "total_to_clear_50ft_ft": round(total)
    }


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