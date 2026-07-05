import numpy as np


alt = np.array([0, 1000, 2000, 3000, 4000, 5000, 6000,
                7000, 8000, 9000, 10000, 11000, 12000], dtype=float)

std_temp = np.array([15, 13, 11, 9, 7, 5, 3, 1, -1, -3, -5, -7, -9], dtype=float)

climb_speed = np.array([73, 73, 72, 72, 71, 71, 70,
                        69, 69, 68, 68, 67, 67], dtype=float)

rate_fpm = np.array([770, 725, 675, 630, 580, 535, 485,
                     440, 390, 345, 295, 250, 200], dtype=float)

time_from_sl = np.array([0, 1, 3, 4, 6, 8, 10,
                         12, 15, 17, 21, 24, 29], dtype=float)

fuel_from_sl = np.array([0.0, 0.3, 0.6, 0.9, 1.2, 1.6, 1.9,
                         2.3, 2.7, 3.2, 3.7, 4.2, 4.9], dtype=float)

distance_from_sl = np.array([0, 2, 3, 5, 8, 10, 12,
                             15, 19, 22, 27, 32, 38], dtype=float)


def table_at(pressure_alt_ft):
    return {
        "std_temp_c": np.interp(pressure_alt_ft, alt, std_temp),
        "climb_speed_kias": np.interp(pressure_alt_ft, alt, climb_speed),
        "rate_fpm": np.interp(pressure_alt_ft, alt, rate_fpm),
        "time_from_sl_min": np.interp(pressure_alt_ft, alt, time_from_sl),
        "fuel_from_sl_gal": np.interp(pressure_alt_ft, alt, fuel_from_sl),
        "distance_from_sl_nm": np.interp(pressure_alt_ft, alt, distance_from_sl),
    }


def climb_from_pressure_alt(pressure_alt_ft, target_alt_ft, oat_c):
    if pressure_alt_ft < alt[0] or pressure_alt_ft > alt[-1]:
        raise ValueError("Pressure altitude out of table range: 0 to 12000 ft")
    if target_alt_ft < alt[0] or target_alt_ft > alt[-1]:
        raise ValueError("Target altitude out of table range: 0 to 12000 ft")
    if target_alt_ft <= pressure_alt_ft:
        raise ValueError("Target altitude must be higher than pressure altitude.")

    start = table_at(pressure_alt_ft)
    target = table_at(target_alt_ft)

    base_time_min = target["time_from_sl_min"] - start["time_from_sl_min"]
    base_fuel_gal = target["fuel_from_sl_gal"] - start["fuel_from_sl_gal"]
    base_distance_nm = target["distance_from_sl_nm"] - start["distance_from_sl_nm"]

    std_oat_at_start = start["std_temp_c"]
    temp_delta = max(oat_c - std_oat_at_start, 0)
    correction = 1 + 0.10 * (temp_delta / 10)

    time_min = base_time_min * correction
    fuel_gal = base_fuel_gal * correction
    distance_nm = base_distance_nm * correction

    result = {
        "pressure_alt_ft": round(pressure_alt_ft, 1),
        "target_alt_ft": round(target_alt_ft, 1),
        "oat_c": round(oat_c, 1),
        "standard_oat_at_pressure_alt_c": round(std_oat_at_start, 1),
        "climb_speed_kias_at_start": round(start["climb_speed_kias"], 1),
        "climb_speed_kias_at_target": round(target["climb_speed_kias"], 1),
        "rate_of_climb_fpm_at_start": round(start["rate_fpm"], 1),
        "rate_of_climb_fpm_at_target": round(target["rate_fpm"], 1),
        "time_to_climb_min": round(time_min, 1),
        "fuel_used_gal_climb_only": round(fuel_gal, 1),
        "fuel_used_gal_with_start_taxi_takeoff": round(fuel_gal + 1.1, 1),
        "distance_to_climb_nm": round(distance_nm, 1),
        "calculation_steps": [
            {
                "title": "1. Inputs",
                "formula": "Pressure altitude, target altitude, OAT",
                "value": f"{pressure_alt_ft:.1f} ft to {target_alt_ft:.1f} ft, OAT {oat_c:.1f} C",
            },
            {
                "title": "2. Start table values",
                "formula": "Interpolate POH Figure 5-6 at pressure altitude",
                "value": (
                    f"Std temp {start['std_temp_c']:.1f} C; speed {start['climb_speed_kias']:.1f} KIAS; "
                    f"ROC {start['rate_fpm']:.1f} fpm; time {start['time_from_sl_min']:.1f} min; "
                    f"fuel {start['fuel_from_sl_gal']:.1f} gal; distance {start['distance_from_sl_nm']:.1f} NM"
                ),
            },
            {
                "title": "3. Target table values",
                "formula": "Interpolate POH Figure 5-6 at target altitude",
                "value": (
                    f"Speed {target['climb_speed_kias']:.1f} KIAS; ROC {target['rate_fpm']:.1f} fpm; "
                    f"time {target['time_from_sl_min']:.1f} min; fuel {target['fuel_from_sl_gal']:.1f} gal; "
                    f"distance {target['distance_from_sl_nm']:.1f} NM"
                ),
            },
            {
                "title": "4. Base climb time",
                "formula": "Target cumulative time - start cumulative time",
                "value": f"{target['time_from_sl_min']:.1f} - {start['time_from_sl_min']:.1f} = {base_time_min:.1f} min",
            },
            {
                "title": "5. Base climb fuel",
                "formula": "Target cumulative fuel - start cumulative fuel",
                "value": f"{target['fuel_from_sl_gal']:.1f} - {start['fuel_from_sl_gal']:.1f} = {base_fuel_gal:.1f} gal",
            },
            {
                "title": "6. Base climb distance",
                "formula": "Target cumulative distance - start cumulative distance",
                "value": f"{target['distance_from_sl_nm']:.1f} - {start['distance_from_sl_nm']:.1f} = {base_distance_nm:.1f} NM",
            },
            {
                "title": "7. Temperature correction",
                "formula": "Add 10% per 10 C above standard temperature",
                "value": (
                    f"OAT {oat_c:.1f} - standard {std_oat_at_start:.1f} = {temp_delta:.1f} C; "
                    f"factor = {correction * 100:.1f}%"
                ),
            },
            {
                "title": "8. Corrected climb values",
                "formula": "Base values x temperature correction factor",
                "value": (
                    f"time {base_time_min:.1f} x {correction * 100:.1f}% = {time_min:.1f} min; "
                    f"fuel {base_fuel_gal:.1f} x {correction * 100:.1f}% = {fuel_gal:.1f} gal; "
                    f"distance {base_distance_nm:.1f} x {correction * 100:.1f}% = {distance_nm:.1f} NM"
                ),
            },
            {
                "title": "9. Start, taxi, takeoff fuel",
                "formula": "Climb fuel + 1.1 gal",
                "value": f"{fuel_gal:.1f} + 1.1 = {fuel_gal + 1.1:.1f} gal",
            },
        ],
    }

    return result
