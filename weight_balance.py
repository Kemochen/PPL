FUEL_LB_PER_GAL = 6.0

BASIC_EMPTY_WEIGHT_LB = 1541.0
BASIC_EMPTY_ARM_IN = 38.2

MAX_RAMP_WEIGHT_LB = 2307.0
MAX_TAKEOFF_WEIGHT_LB = 2300.0
MAX_LANDING_WEIGHT_LB = 2300.0

ARM_FRONT_SEATS_IN = 40.0
ARM_REAR_SEATS_IN = 73.0
ARM_BAGGAGE_1_IN = 95.0
ARM_BAGGAGE_2_IN = 123.0
ARM_FUEL_IN = 48.0


def r1(value):
    return round(float(value), 1)


def moment(weight_lbs, arm_in):
    return weight_lbs * arm_in


def cg(weight_lbs, moment_lb_in):
    if weight_lbs <= 0:
        raise ValueError("Total weight must be greater than zero.")
    return moment_lb_in / weight_lbs


def normal_category_cg_limits(weight_lbs):
    # C172N normal category landplane: 35.0 in at 1950 lb or less,
    # straight-line forward limit to 38.5 in at 2300 lb; aft limit 47.3 in.
    if weight_lbs <= 1950.0:
        forward = 35.0
    else:
        forward = 35.0 + ((weight_lbs - 1950.0) / 350.0) * (38.5 - 35.0)
    return forward, 47.3


def status_for_phase(phase, weight_lbs, cg_in, max_weight_lbs):
    forward, aft = normal_category_cg_limits(weight_lbs)
    if weight_lbs > max_weight_lbs:
        return "FAIL", f"OVER MAX {phase.upper()} WEIGHT", forward, aft
    if cg_in < forward:
        return "FAIL", "CG FORWARD OF LIMIT", forward, aft
    if cg_in > aft:
        return "FAIL", "CG AFT OF LIMIT", forward, aft
    return "OK", "Within limits", forward, aft


def load_row(item, arm, weight):
    return {
        "item": item,
        "arm": r1(arm),
        "weight": r1(weight),
        "moment": r1(moment(weight, arm)),
        "cg": None,
        "kind": "load",
    }


def total_row(item, weight, moment_value):
    return {
        "item": item,
        "arm": None,
        "weight": r1(weight),
        "moment": r1(moment_value),
        "cg": r1(cg(weight, moment_value)),
        "kind": "total",
    }


def make_explanation(title, lines):
    return {"title": title, "lines": lines}


def calculate_weight_balance(
    pilot_weight_lbs,
    front_passenger_weight_lbs,
    rear_left_weight_lbs,
    rear_right_weight_lbs,
    baggage1_weight_lbs,
    baggage2_weight_lbs,
    fuel_gal,
    taxi_fuel_gal,
    trip_fuel_gal,
    empty_weight_lbs=BASIC_EMPTY_WEIGHT_LB,
    empty_arm_in=BASIC_EMPTY_ARM_IN,
):
    weights = [
        pilot_weight_lbs,
        front_passenger_weight_lbs,
        rear_left_weight_lbs,
        rear_right_weight_lbs,
        baggage1_weight_lbs,
        baggage2_weight_lbs,
        fuel_gal,
        taxi_fuel_gal,
        trip_fuel_gal,
        empty_weight_lbs,
    ]
    if any(value < 0 for value in weights):
        raise ValueError("Weights and fuel quantities cannot be negative.")

    empty_moment = moment(empty_weight_lbs, empty_arm_in)
    pilot = load_row("Pilot", ARM_FRONT_SEATS_IN, pilot_weight_lbs)
    passenger = load_row("Front Passenger", ARM_FRONT_SEATS_IN, front_passenger_weight_lbs)
    rear_left = load_row("Rear Left", ARM_REAR_SEATS_IN, rear_left_weight_lbs)
    rear_right = load_row("Rear Right", ARM_REAR_SEATS_IN, rear_right_weight_lbs)
    baggage1 = load_row("Baggage 1", ARM_BAGGAGE_1_IN, baggage1_weight_lbs)
    baggage2 = load_row("Baggage 2", ARM_BAGGAGE_2_IN, baggage2_weight_lbs)

    occupant_baggage_weight = sum(row["weight"] for row in [pilot, passenger, rear_left, rear_right, baggage1, baggage2])
    occupant_baggage_moment = sum(row["moment"] for row in [pilot, passenger, rear_left, rear_right, baggage1, baggage2])

    zero_fuel_weight = empty_weight_lbs + occupant_baggage_weight
    zero_fuel_moment = empty_moment + occupant_baggage_moment

    fuel_weight = fuel_gal * FUEL_LB_PER_GAL
    taxi_fuel_weight = taxi_fuel_gal * FUEL_LB_PER_GAL
    trip_fuel_weight = trip_fuel_gal * FUEL_LB_PER_GAL

    fuel_moment = moment(fuel_weight, ARM_FUEL_IN)
    taxi_fuel_moment = moment(taxi_fuel_weight, ARM_FUEL_IN)
    trip_fuel_moment = moment(trip_fuel_weight, ARM_FUEL_IN)

    ramp_weight = zero_fuel_weight + fuel_weight
    ramp_moment = zero_fuel_moment + fuel_moment

    takeoff_weight = ramp_weight - taxi_fuel_weight
    takeoff_moment = ramp_moment - taxi_fuel_moment

    landing_weight = takeoff_weight - trip_fuel_weight
    landing_moment = takeoff_moment - trip_fuel_moment

    phases = [
        ("ZFW", zero_fuel_weight, zero_fuel_moment, MAX_TAKEOFF_WEIGHT_LB),
        ("Ramp", ramp_weight, ramp_moment, MAX_RAMP_WEIGHT_LB),
        ("Takeoff", takeoff_weight, takeoff_moment, MAX_TAKEOFF_WEIGHT_LB),
        ("Landing", landing_weight, landing_moment, MAX_LANDING_WEIGHT_LB),
    ]

    envelope = []
    for phase, weight, moment_value, max_weight in phases:
        cg_value = cg(weight, moment_value)
        status, message, forward, aft = status_for_phase(phase, weight, cg_value, max_weight)
        envelope.append({
            "phase": phase,
            "weight": r1(weight),
            "max_weight": r1(max_weight),
            "cg": r1(cg_value),
            "forward_limit": r1(forward),
            "aft_limit": r1(aft),
            "limit": f"{forward:.1f} - {aft:.1f}",
            "status": status,
            "message": message,
        })

    rows = [
        {
            "item": "Empty Aircraft",
            "arm": r1(empty_arm_in),
            "weight": r1(empty_weight_lbs),
            "moment": r1(empty_moment),
            "cg": None,
            "kind": "load",
        },
        pilot,
        passenger,
        rear_left,
        rear_right,
        baggage1,
        baggage2,
        total_row("Zero Fuel", zero_fuel_weight, zero_fuel_moment),
        load_row("Fuel", ARM_FUEL_IN, fuel_weight),
        total_row("Ramp", ramp_weight, ramp_moment),
        {
            "item": "Taxi Fuel",
            "arm": r1(-ARM_FUEL_IN),
            "weight": r1(-taxi_fuel_weight),
            "moment": r1(-taxi_fuel_moment),
            "cg": None,
            "kind": "burn",
        },
        total_row("Takeoff", takeoff_weight, takeoff_moment),
        {
            "item": "Trip Fuel",
            "arm": r1(-ARM_FUEL_IN),
            "weight": r1(-trip_fuel_weight),
            "moment": r1(-trip_fuel_moment),
            "cg": None,
            "kind": "burn",
        },
        total_row("Landing", landing_weight, landing_moment),
    ]

    moment_steps = [
        {
            "title": "Moment - Empty Aircraft",
            "formula": "Moment = weight x arm",
            "value": f"{empty_weight_lbs:.1f} x {empty_arm_in:.1f} = {empty_moment:.1f} lb-in",
        },
        {
            "title": "Moment - Pilot",
            "formula": "Moment = weight x arm",
            "value": f"{pilot_weight_lbs:.1f} x 40.0 = {pilot['moment']:.1f} lb-in",
        },
        {
            "title": "Moment - Front Passenger",
            "formula": "Moment = weight x arm",
            "value": f"{front_passenger_weight_lbs:.1f} x 40.0 = {passenger['moment']:.1f} lb-in",
        },
        {
            "title": "Moment - Rear Left",
            "formula": "Moment = weight x arm",
            "value": f"{rear_left_weight_lbs:.1f} x 73.0 = {rear_left['moment']:.1f} lb-in",
        },
        {
            "title": "Moment - Rear Right",
            "formula": "Moment = weight x arm",
            "value": f"{rear_right_weight_lbs:.1f} x 73.0 = {rear_right['moment']:.1f} lb-in",
        },
        {
            "title": "Moment - Baggage 1",
            "formula": "Moment = weight x arm",
            "value": f"{baggage1_weight_lbs:.1f} x 95.0 = {baggage1['moment']:.1f} lb-in",
        },
        {
            "title": "Moment - Baggage 2",
            "formula": "Moment = weight x arm",
            "value": f"{baggage2_weight_lbs:.1f} x 123.0 = {baggage2['moment']:.1f} lb-in",
        },
        {
            "title": "Moment - Fuel",
            "formula": "Fuel moment = fuel weight x 48",
            "value": f"{fuel_weight:.1f} x 48.0 = {fuel_moment:.1f} lb-in",
        },
        {
            "title": "Moment - Taxi Fuel",
            "formula": "Removed fuel moment = -fuel weight x 48",
            "value": f"-{taxi_fuel_weight:.1f} x 48.0 = {-taxi_fuel_moment:.1f} lb-in",
        },
        {
            "title": "Moment - Trip Fuel",
            "formula": "Removed fuel moment = -fuel weight x 48",
            "value": f"-{trip_fuel_weight:.1f} x 48.0 = {-trip_fuel_moment:.1f} lb-in",
        },
    ]

    steps = [
        {
            "title": "Fuel conversion",
            "formula": "Fuel weight = gallons x 6",
            "value": (
                f"Fuel {fuel_gal:.1f} x 6 = {fuel_weight:.1f} lb; "
                f"Taxi {taxi_fuel_gal:.1f} x 6 = {taxi_fuel_weight:.1f} lb; "
                f"Trip {trip_fuel_gal:.1f} x 6 = {trip_fuel_weight:.1f} lb"
            ),
        },
        *moment_steps,
        {
            "title": "Zero Fuel",
            "formula": "Empty aircraft + occupants + baggage",
            "value": (
                f"Weight {empty_weight_lbs:.1f} + {occupant_baggage_weight:.1f} = {zero_fuel_weight:.1f}; "
                f"Moment {empty_moment:.1f} + {occupant_baggage_moment:.1f} = {zero_fuel_moment:.1f}; "
                f"CG {zero_fuel_moment:.1f} / {zero_fuel_weight:.1f} = {cg(zero_fuel_weight, zero_fuel_moment):.1f}"
            ),
        },
        {
            "title": "Ramp",
            "formula": "Zero Fuel + usable fuel",
            "value": (
                f"Weight {zero_fuel_weight:.1f} + {fuel_weight:.1f} = {ramp_weight:.1f}; "
                f"Moment {zero_fuel_moment:.1f} + {fuel_moment:.1f} = {ramp_moment:.1f}; "
                f"CG {ramp_moment:.1f} / {ramp_weight:.1f} = {cg(ramp_weight, ramp_moment):.1f}"
            ),
        },
        {
            "title": "Takeoff",
            "formula": "Ramp - taxi fuel",
            "value": (
                f"Weight {ramp_weight:.1f} - {taxi_fuel_weight:.1f} = {takeoff_weight:.1f}; "
                f"Moment {ramp_moment:.1f} - {taxi_fuel_moment:.1f} = {takeoff_moment:.1f}; "
                f"CG {takeoff_moment:.1f} / {takeoff_weight:.1f} = {cg(takeoff_weight, takeoff_moment):.1f}"
            ),
        },
        {
            "title": "Landing",
            "formula": "Takeoff - trip fuel",
            "value": (
                f"Weight {takeoff_weight:.1f} - {trip_fuel_weight:.1f} = {landing_weight:.1f}; "
                f"Moment {takeoff_moment:.1f} - {trip_fuel_moment:.1f} = {landing_moment:.1f}; "
                f"CG {landing_moment:.1f} / {landing_weight:.1f} = {cg(landing_weight, landing_moment):.1f}"
            ),
        },
    ]

    explanations = [
        make_explanation("Fuel Weight", [
            f"Fuel weight = gallons x 6.",
            f"{fuel_gal:.1f} gal x 6 = {fuel_weight:.1f} lb.",
            f"Fuel moment = {fuel_weight:.1f} x 48.0 = {fuel_moment:.1f} lb-in.",
        ]),
        make_explanation("Zero Fuel CG", [
            f"Zero Fuel Weight = Empty Aircraft + occupants + baggage = {zero_fuel_weight:.1f} lb.",
            f"Zero Fuel Moment = {zero_fuel_moment:.1f} lb-in.",
            f"Zero Fuel CG = {zero_fuel_moment:.1f} / {zero_fuel_weight:.1f} = {cg(zero_fuel_weight, zero_fuel_moment):.1f} in.",
        ]),
        make_explanation("Takeoff Weight", [
            f"Ramp Weight = {ramp_weight:.1f} lb.",
            f"Taxi Fuel = {taxi_fuel_gal:.1f} gal x 6 = {taxi_fuel_weight:.1f} lb.",
            f"Takeoff Weight = {ramp_weight:.1f} - {taxi_fuel_weight:.1f} = {takeoff_weight:.1f} lb.",
        ]),
        make_explanation("Landing CG", [
            f"Landing Moment = Takeoff Moment - Trip Fuel Moment.",
            f"{takeoff_moment:.1f} - {trip_fuel_moment:.1f} = {landing_moment:.1f} lb-in.",
            f"Landing CG = {landing_moment:.1f} / {landing_weight:.1f} = {cg(landing_weight, landing_moment):.1f} in.",
        ]),
    ]

    return {
        "kind": "weight_balance",
        "summary": {
            "zero_fuel_cg_in": r1(cg(zero_fuel_weight, zero_fuel_moment)),
            "ramp_cg_in": r1(cg(ramp_weight, ramp_moment)),
            "takeoff_cg_in": r1(cg(takeoff_weight, takeoff_moment)),
            "landing_cg_in": r1(cg(landing_weight, landing_moment)),
            "takeoff_weight_lbs": r1(takeoff_weight),
            "landing_weight_lbs": r1(landing_weight),
        },
        "rows": rows,
        "envelope": envelope,
        "explanations": explanations,
        "plot": {
            "envelope": [
                {"cg": 35.0, "weight": 1500.0},
                {"cg": 35.0, "weight": 1950.0},
                {"cg": 38.5, "weight": 2300.0},
                {"cg": 47.3, "weight": 2300.0},
                {"cg": 47.3, "weight": 1500.0},
            ],
            "points": [
                {"label": row["phase"], "cg": row["cg"], "weight": row["weight"], "status": row["status"]}
                for row in envelope
            ],
        },
        "calculation_steps": steps,
    }
