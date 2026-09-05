"""Passenger emergency exit configuration logic (vehicle-design/sizing).

Discrete certification-style checks for a passenger emergency exit
configuration: per-type minimum opening and seating credit lookup (the
exit-type lookup of the SKILL.md workflow), per-side capacity sums, the
capacity-band required per-side exit set, the exit-count-check verdicts for
each side of the fuselage, the 60 ft adjacent-exit spacing rule on one side,
and the aggregate evacuation demand ratio. Pure stdlib, deterministic, no
network, no external processes.

The exit type definitions and per-exit seating credits are paraphrased
module constants (far-25 referenced, not reproduced; standards-map.yaml).
"""

from itertools import combinations_with_replacement

# Public regulatory type definitions and per-exit credit table paraphrased
# into module constants: exit type id -> (width_in, height_in,
# seating_credit). The credit encodes the maximum seating that follows from
# the type and number of exits installed on a side (110 for a Type A on a
# side, 75 for a Type B, and so on).
EXIT_TYPES = {
    "A": (42, 72, 110),
    "B": (32, 72, 75),
    "C": (30, 48, 55),
    "I": (24, 48, 45),
    "II": (20, 44, 40),
    "III": (20, 36, 35),
    "IV": (19, 26, 9),
}

# Type size ordering, smallest to largest: IV < III < II < I < C < B < A.
TYPE_RANK = {"IV": 0, "III": 1, "II": 2, "I": 3, "C": 4, "B": 5, "A": 6}

# 60 ft adjacent-exit spacing rule limit (centerline gap on the same side).
MAX_ADJACENT_EXIT_SPACING_FT = 60.0

# Exact enumeration cap for the required per-side exit set search.
MAX_EXITS_PER_SIDE = 12

# Capacity band rules (paraphrase of the discrete type-and-number rules).
# Fields: band label, seat range, minimum exit count per side, the named
# large-exit minimum the side must carry ("one_exit_min" or, for the >110
# band, "two_exits_min"), the per-exit floor "all_exits_min", and the
# smallest type ("enum_min") the required-set search may draw from.
CAPACITY_BANDS = [
    {
        "band": "1-9",
        "min_seats": 1,
        "max_seats": 9,
        "min_exits_per_side": 1,
        "one_exit_min": "IV",
        "two_exits_min": None,
        "all_exits_min": None,
        "enum_min": "IV",
    },
    {
        "band": "10-19",
        "min_seats": 10,
        "max_seats": 19,
        "min_exits_per_side": 1,
        "one_exit_min": "III",
        "two_exits_min": None,
        "all_exits_min": None,
        "enum_min": "III",
    },
    {
        "band": "20-40",
        "min_seats": 20,
        "max_seats": 40,
        "min_exits_per_side": 2,
        "one_exit_min": "II",
        "two_exits_min": None,
        "all_exits_min": None,
        "enum_min": "III",
    },
    {
        "band": "41-110",
        "min_seats": 41,
        "max_seats": 110,
        "min_exits_per_side": 2,
        "one_exit_min": "I",
        "two_exits_min": None,
        "all_exits_min": None,
        "enum_min": "III",
    },
    {
        "band": ">110",
        "min_seats": 111,
        "max_seats": None,
        "min_exits_per_side": 2,
        "one_exit_min": None,
        "two_exits_min": "I",
        "all_exits_min": "III",
        "enum_min": "III",
    },
]


def _raise_unknown_type(exit_type):
    """Raise ValueError for an exit type outside the constant table."""
    known = ", ".join(sorted(EXIT_TYPES, key=lambda t: TYPE_RANK[t]))
    raise ValueError("unknown exit type %r (known types: %s)" % (exit_type, known))


def _check_type(exit_type):
    """Guard helper: ValueError for an unknown exit type id."""
    if exit_type not in EXIT_TYPES:
        _raise_unknown_type(exit_type)


def capacity_band(passenger_capacity):
    """Return the capacity band rule dict for a passenger capacity.

    Step 4 of the SKILL.md workflow: the band selects the minimum exit
    count and the minimum types a per-side configuration must honor.
    """
    for rule in CAPACITY_BANDS:
        if rule["max_seats"] is not None and passenger_capacity <= rule["max_seats"]:
            return rule
    return CAPACITY_BANDS[-1]


def exit_type_dimensions(exit_type):
    """Look up one exit type: minimum rectangular opening and credit.

    Step 2 of the SKILL.md workflow, the exit-type lookup against the
    module constant table. Returns a dict with keys width_in, height_in,
    seating_credit. ValueError for an unknown type.
    """
    _check_type(exit_type)
    width_in, height_in, seating_credit = EXIT_TYPES[exit_type]
    return {
        "width_in": width_in,
        "height_in": height_in,
        "seating_credit": seating_credit,
    }


def side_exit_capacity(exits):
    """Sum the seating credits of the installed exit types on one side.

    Step 3 of the SKILL.md workflow: the per-side capacity sum that must
    alone cover the passenger capacity (an emergency can make one side
    unusable, so each side must suffice). ValueError for an unknown type.
    """
    for exit_type in exits:
        _check_type(exit_type)
    return sum(EXIT_TYPES[exit_type][2] for exit_type in exits)


def _honors_large_types(combo, rule):
    """True when an exit multiset carries the band's large-type minimums."""
    if rule["one_exit_min"] is not None:
        if not any(TYPE_RANK[t] >= TYPE_RANK[rule["one_exit_min"]] for t in combo):
            return False
    if rule["two_exits_min"] is not None:
        large = sum(1 for t in combo if TYPE_RANK[t] >= TYPE_RANK[rule["two_exits_min"]])
        if large < 2:
            return False
    if rule["all_exits_min"] is not None:
        if not all(TYPE_RANK[t] >= TYPE_RANK[rule["all_exits_min"]] for t in combo):
            return False
    return True


def required_exits_by_capacity(passenger_capacity):
    """Smallest-count per-side exit multiset that covers the capacity.

    Step 4 of the SKILL.md workflow: the required per-side exit set. Exact
    enumeration over combinations with replacement up to 12 exits per side
    from the types the band allows, honoring the band minimum count and
    minimum types; ties broken by the smaller excess. ValueError for a
    capacity below 1 or above the per-side coverage ceiling.
    """
    if passenger_capacity < 1:
        raise ValueError("passenger capacity must be at least 1")
    rule = capacity_band(passenger_capacity)
    floor = TYPE_RANK[rule["enum_min"]]
    allowed = sorted((t for t in EXIT_TYPES if TYPE_RANK[t] >= floor),
                     key=lambda t: TYPE_RANK[t])
    for count in range(rule["min_exits_per_side"], MAX_EXITS_PER_SIDE + 1):
        best_excess = None
        best_covered = 0
        best_required = None
        for combo in combinations_with_replacement(allowed, count):
            if not _honors_large_types(combo, rule):
                continue
            covered = sum(EXIT_TYPES[t][2] for t in combo)
            if covered < passenger_capacity:
                continue
            excess = covered - passenger_capacity
            if best_excess is None or excess < best_excess:
                best_excess = excess
                best_covered = covered
                best_required = sorted(combo, key=lambda t: TYPE_RANK[t], reverse=True)
        if best_required is not None:
            return {
                "band": rule["band"],
                "min_exits_per_side": rule["min_exits_per_side"],
                "required_per_side": best_required,
                "covered": best_covered,
                "excess_seats": best_excess,
            }
    raise ValueError(
        "passenger capacity %d exceeds the maximum per-side exit coverage "
        "of %d seats with up to %d exits per side"
        % (passenger_capacity, MAX_EXITS_PER_SIDE * EXIT_TYPES["A"][2],
           MAX_EXITS_PER_SIDE))


def _side_verdict(passenger_capacity, exits, rule):
    """Per-side failures of the exit-count-check for one fuselage side."""
    failures = []
    for exit_type in exits:
        _check_type(exit_type)
    credit_sum = sum(EXIT_TYPES[t][2] for t in exits)
    if credit_sum < passenger_capacity:
        failures.append("capacity")
    if len(exits) < rule["min_exits_per_side"]:
        failures.append("minimum-exit-count")
    if rule["all_exits_min"] is not None:
        if any(TYPE_RANK[t] < TYPE_RANK[rule["all_exits_min"]] for t in exits):
            failures.append("all-exits-minimum-type")
    if rule["one_exit_min"] is not None:
        if not any(TYPE_RANK[t] >= TYPE_RANK[rule["one_exit_min"]] for t in exits):
            failures.append("one-exit-minimum-type")
    if rule["two_exits_min"] is not None:
        large = sum(1 for t in exits if TYPE_RANK[t] >= TYPE_RANK[rule["two_exits_min"]])
        if large < 2:
            failures.append("two-exits-minimum-type")
    c_or_larger = sum(1 for t in exits if TYPE_RANK[t] >= TYPE_RANK["C"])
    if c_or_larger == 1:
        failures.append("two-C-or-larger-when-ABC-installed")
    return credit_sum, failures


def exit_count_check(passenger_capacity, left_exits, right_exits):
    """Verdict dict for the exits installed on both sides of the fuselage.

    Step 5 of the SKILL.md workflow, the exit-count-check: per side the
    credit sum must cover the capacity, the band minimum count and minimum
    types must hold, and when any Type A/B/C exit is installed the side
    must carry at least two exits of Type C or larger. ValueErrors: unknown
    type, capacity below 1.
    """
    if passenger_capacity < 1:
        raise ValueError("passenger capacity must be at least 1")
    rule = capacity_band(passenger_capacity)
    left_capacity, left_failures = _side_verdict(passenger_capacity, left_exits, rule)
    right_capacity, right_failures = _side_verdict(passenger_capacity, right_exits, rule)
    shortfall = max(0, passenger_capacity - min(left_capacity, right_capacity))
    return {
        "passenger_capacity": passenger_capacity,
        "left_exits": list(left_exits),
        "left_capacity": left_capacity,
        "left_failures": left_failures,
        "right_exits": list(right_exits),
        "right_capacity": right_capacity,
        "right_failures": right_failures,
        "adequate": not left_failures and not right_failures,
        "shortfall": shortfall,
    }


def exit_placement_check(exit_row_numbers, seat_pitch_in):
    """Check the 60 ft adjacent-exit spacing rule on one side.

    Step 6 of the SKILL.md workflow, the adjacent-exit spacing rule:
    consecutive exits on the same side are separated by the row difference
    times the seat pitch (converted to feet); any centerline gap above
    60 ft is a spacing violation, and the implied maximum seat distance to
    an exit is half the largest adjacent gap. ValueErrors: empty or
    non-positive row lists, pitch at or below 0.
    """
    if not exit_row_numbers:
        raise ValueError("at least one exit row is required")
    rows = sorted(int(row) for row in exit_row_numbers)
    if rows[0] < 1:
        raise ValueError("exit rows must be positive integers")
    if seat_pitch_in <= 0:
        raise ValueError("seat pitch must be positive")
    gaps = [
        (later - earlier) * seat_pitch_in / 12.0
        for earlier, later in zip(rows, rows[1:])
    ]
    violations = [
        (index, gap)
        for index, gap in enumerate(gaps, start=1)
        if gap > MAX_ADJACENT_EXIT_SPACING_FT
    ]
    max_gap = max(gaps) if gaps else 0.0
    return {
        "exit_row_numbers": rows,
        "adjacent_gap_ft": gaps,
        "spacing_violations": violations,
        "adequate": not violations,
        "max_implied_seat_distance_ft": max_gap / 2.0,
    }


def evacuation_demand_ratio(passenger_capacity, exit_capacity_sum):
    """Aggregate evacuation demand ratio: capacity over the exit credit sum.

    Step 7 of the SKILL.md workflow: a ratio at or below 1.0 means the
    aggregate exit capacity covers the cabin. ValueErrors: capacity below
    1, exit capacity sum at or below 0.
    """
    if passenger_capacity < 1:
        raise ValueError("passenger capacity must be at least 1")
    if exit_capacity_sum <= 0:
        raise ValueError("exit capacity sum must be positive")
    return passenger_capacity / exit_capacity_sum
