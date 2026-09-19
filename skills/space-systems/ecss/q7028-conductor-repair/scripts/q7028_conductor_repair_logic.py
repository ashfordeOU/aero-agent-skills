"""Conductor and track repair on printed-circuit-board assemblies.

Anchor: ECSS-Q-ST-70-28C, methods clause -- restoring a broken, cut or lifted
conductor either by soldering a replacement segment lapped over the surviving
track, or by running an insulated jumper wire between two sound points.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Choose the method from the gap in the conductor and the width of the track:
   a short gap on a track wide enough to solder to takes a lapped replacement
   segment; anything longer takes a jumper wire; past the jumper reach there
   is no method.
2. Size a lap joint: the overlap each end needs from the track width, and the
   length of replacement conductor that follows.
3. Size a jumper wire from the circuit current and a derating on the current
   the wire cross-section carries, then count the bonds that hold it down over
   its unsupported run.
4. Compare the replacement cross-section against the copper it replaces, so a
   restored conductor is not thinner than the one that failed.
5. Return the repair with every finding that would send it back.
"""

import math

__all__ = [
    "MAX_LAP_GAP_MM",
    "MIN_LAP_TRACK_WIDTH_MM",
    "MAX_JUMPER_LENGTH_MM",
    "LAP_OVERLAP_FACTOR",
    "MIN_LAP_OVERLAP_MM",
    "MAX_UNSUPPORTED_RUN_MM",
    "MAX_JUMPERS_PER_BOARD",
    "COPPER_THICKNESS_MM_PER_OZ",
    "JUMPER_CURRENT_DENSITY_A_PER_MM2",
    "JUMPER_DERATING",
    "WIRE_GAUGES_MM",
    "GEOMETRY_TOLERANCE_MM",
    "CURRENT_TOLERANCE_A",
    "track_cross_section_mm2",
    "wire_cross_section_mm2",
    "lap_overlap_mm",
    "lap_segment_length_mm",
    "select_method",
    "select_jumper_gauge",
    "jumper_bond_count",
    "plan_conductor_repair",
]

# A gap this long or shorter, on a track this wide or wider, is lapped.
MAX_LAP_GAP_MM = 2.0
MIN_LAP_TRACK_WIDTH_MM = 0.40

# The longest run a jumper wire may take before the repair is refused.
MAX_JUMPER_LENGTH_MM = 75.0

# Overlap at each end of a lapped replacement segment.
LAP_OVERLAP_FACTOR = 3.0
MIN_LAP_OVERLAP_MM = 1.0

# A jumper is bonded down at least this often along its run, and a board only
# carries so many of them before it is a rebuild rather than a repair.
MAX_UNSUPPORTED_RUN_MM = 25.0
MAX_JUMPERS_PER_BOARD = 5

# Finished copper thickness per ounce of copper weight, in millimetres.
COPPER_THICKNESS_MM_PER_OZ = 0.0347

# Current a jumper conductor carries per square millimetre, and the derating
# applied to it on a repaired board.
JUMPER_CURRENT_DENSITY_A_PER_MM2 = 6.0
JUMPER_DERATING = 0.80

# Solid wire gauges available at the repair bench: gauge number -> diameter mm.
# Listed thinnest first so the search returns the smallest adequate wire.
WIRE_GAUGES_MM = (
    (30, 0.255),
    (28, 0.321),
    (26, 0.405),
    (24, 0.511),
    (22, 0.644),
    (20, 0.812),
)

# Dimensions and currents are measured quantities; a value on a bound is inside.
GEOMETRY_TOLERANCE_MM = 1e-9
CURRENT_TOLERANCE_A = 1e-9


def _positive(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _count(value, label):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def track_cross_section_mm2(track_width_mm, copper_weight_oz):
    """Return the cross-section of the original track in square millimetres."""
    width = _positive(track_width_mm, "track_width_mm")
    weight = _positive(copper_weight_oz, "copper_weight_oz")
    return width * weight * COPPER_THICKNESS_MM_PER_OZ


def wire_cross_section_mm2(diameter_mm):
    """Return the cross-section of a round wire in square millimetres."""
    diameter = _positive(diameter_mm, "diameter_mm")
    return math.pi * diameter * diameter / 4.0


def lap_overlap_mm(track_width_mm):
    """Return the overlap one end of a lapped replacement segment needs."""
    width = _positive(track_width_mm, "track_width_mm")
    return max(MIN_LAP_OVERLAP_MM, LAP_OVERLAP_FACTOR * width)


def lap_segment_length_mm(gap_mm, track_width_mm):
    """Return the total length of replacement conductor a lap joint consumes."""
    gap = _positive(gap_mm, "gap_mm")
    return gap + 2.0 * lap_overlap_mm(track_width_mm)


def select_method(gap_mm, track_width_mm):
    """Choose between a lapped segment, a jumper wire, or no method at all."""
    gap = _positive(gap_mm, "gap_mm")
    width = _positive(track_width_mm, "track_width_mm")
    if gap > MAX_JUMPER_LENGTH_MM + GEOMETRY_TOLERANCE_MM:
        return {
            "method": None,
            "reason": "a gap of %g mm is past the %g mm a jumper may span; the board "
            "goes to nonconformance review" % (gap, MAX_JUMPER_LENGTH_MM),
        }
    lappable = (
        gap <= MAX_LAP_GAP_MM + GEOMETRY_TOLERANCE_MM
        and width >= MIN_LAP_TRACK_WIDTH_MM - GEOMETRY_TOLERANCE_MM
    )
    if lappable:
        return {"method": "conductor-lap-solder-splice", "reason": None}
    if gap <= MAX_LAP_GAP_MM + GEOMETRY_TOLERANCE_MM:
        return {
            "method": "conductor-jumper-wire",
            "reason": "the track is %g mm wide, under the %g mm a lap joint needs to "
            "solder to" % (width, MIN_LAP_TRACK_WIDTH_MM),
        }
    return {
        "method": "conductor-jumper-wire",
        "reason": "a gap of %g mm is past the %g mm a lap joint spans"
        % (gap, MAX_LAP_GAP_MM),
    }


def select_jumper_gauge(current_a, derating=JUMPER_DERATING):
    """Return the thinnest bench wire that carries the derated circuit current."""
    current = _positive(current_a, "current_a")
    factor = _positive(derating, "derating")
    if factor > 1.0:
        raise ValueError("derating must not exceed 1.0, got %g" % factor)
    for gauge, diameter in WIRE_GAUGES_MM:
        area = wire_cross_section_mm2(diameter)
        capacity = area * JUMPER_CURRENT_DENSITY_A_PER_MM2 * factor
        if capacity >= current - CURRENT_TOLERANCE_A:
            return {
                "gauge": gauge,
                "diameter_mm": diameter,
                "cross_section_mm2": area,
                "derated_capacity_a": capacity,
            }
    raise ValueError(
        "no bench wire carries %g A at a derating of %g; route the current another way"
        % (current, factor)
    )


def jumper_bond_count(length_mm):
    """Return how many bonds hold a jumper of this length down."""
    length = _positive(length_mm, "length_mm")
    spans = int(math.ceil(length / MAX_UNSUPPORTED_RUN_MM - GEOMETRY_TOLERANCE_MM))
    return max(1, spans) + 1


def plan_conductor_repair(damage):
    """Plan one conductor repair and return it with every finding.

    damage keys: gap_mm, track_width_mm, copper_weight_oz, current_a, optional
    jumper_route_length_mm, existing_jumpers and derating.
    """
    if not isinstance(damage, dict):
        raise ValueError("damage must be a mapping")
    for key in ("gap_mm", "track_width_mm", "copper_weight_oz", "current_a"):
        if key not in damage:
            raise ValueError("damage missing required key '%s'" % key)

    findings = []
    selection = select_method(damage["gap_mm"], damage["track_width_mm"])
    method = selection["method"]
    if method is None:
        findings.append(selection["reason"])

    original_area = track_cross_section_mm2(
        damage["track_width_mm"], damage["copper_weight_oz"]
    )

    overlap = None
    segment_length = None
    jumper = None
    bonds = None
    route_length = None

    if method == "conductor-lap-solder-splice":
        overlap = lap_overlap_mm(damage["track_width_mm"])
        segment_length = lap_segment_length_mm(damage["gap_mm"], damage["track_width_mm"])
        replacement_area = original_area
    elif method == "conductor-jumper-wire":
        jumper = select_jumper_gauge(
            damage["current_a"], damage.get("derating", JUMPER_DERATING)
        )
        replacement_area = jumper["cross_section_mm2"]
        route_length = _positive(
            damage.get("jumper_route_length_mm", damage["gap_mm"]),
            "jumper_route_length_mm",
        )
        if route_length > MAX_JUMPER_LENGTH_MM + GEOMETRY_TOLERANCE_MM:
            findings.append(
                "the jumper route of %g mm is past the %g mm a jumper may span"
                % (route_length, MAX_JUMPER_LENGTH_MM)
            )
        bonds = jumper_bond_count(route_length)
        existing = _count(damage.get("existing_jumpers", 0), "existing_jumpers")
        if existing + 1 > MAX_JUMPERS_PER_BOARD:
            findings.append(
                "this would be jumper %d on the board, past the %d allowed"
                % (existing + 1, MAX_JUMPERS_PER_BOARD)
            )
    else:
        replacement_area = 0.0

    if method is not None and replacement_area < original_area - GEOMETRY_TOLERANCE_MM:
        findings.append(
            "the replacement conductor is %.5f mm2 against the %.5f mm2 it replaces; "
            "the repaired path would be the new weakest point"
            % (replacement_area, original_area)
        )

    return {
        "method": method,
        "method_reason": selection["reason"],
        "original_cross_section_mm2": original_area,
        "replacement_cross_section_mm2": replacement_area,
        "lap_overlap_mm": overlap,
        "lap_segment_length_mm": segment_length,
        "jumper": jumper,
        "jumper_route_length_mm": route_length,
        "jumper_bonds": bonds,
        "findings": findings,
        "ready": not findings,
    }
