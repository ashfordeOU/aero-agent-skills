"""Solid-wire wrapping operation on a wrapping post.

Anchor: ECSS-Q-ST-70-30C, wrapping process clauses (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Fix what the wire gauge owes. A wrapped connection holds because a
   defined number of turns of bare conductor is pressed onto the post
   corners, and the finer the conductor the more turns it takes to
   reach the same joint. The turn schedule is therefore a property of
   the gauge, not of the operator.
2. Add the insulated turns the wrap configuration carries. A modified
   wrap starts with part of a turn of insulated wire so the conductor
   is supported where it leaves the wrap and cannot be broken by
   vibration at that point; a conventional wrap carries none, and an
   insulated turn on a conventional wrap is as much a departure as a
   missing one on a modified wrap.
3. Compute the height the wrap occupies. Turns are laid adjacent, so
   the height is the turn count multiplied by the diameter of what is
   being laid -- the bare conductor for a bare turn, the conductor plus
   both insulation walls for an insulated turn.
4. Fit the wrap on the post. The usable post length is what is left
   after the base offset and the levels already wrapped, and a wrap
   that does not fit inside it is refused before it is made rather
   than trimmed afterwards.
5. Grade tightness and position. Every bare turn has to seat on every
   corner of the post, the gap between adjacent turns is bounded by a
   fraction of the conductor diameter, and the first level starts at
   the base of the post while a later level starts on top of the one
   below it.

Every threshold here is a declared project policy value and can be
overridden by the caller, because the schedule a programme adopts is
part of its own process specification.

Stdlib only, offline, deterministic.
"""

WRAP_MODIFIED = "modified"
WRAP_CONVENTIONAL = "conventional"
VALID_WRAP_TYPES = (WRAP_MODIFIED, WRAP_CONVENTIONAL)

# Representative turn schedule: conductor diameter in millimetres and
# the minimum number of bare turns the gauge owes. Declared policy, not
# a reproduction of the standard's table.
WIRE_GAUGE_SCHEDULE = {
    20: {"conductor_diameter_mm": 0.813, "min_bare_turns": 4},
    22: {"conductor_diameter_mm": 0.643, "min_bare_turns": 5},
    24: {"conductor_diameter_mm": 0.511, "min_bare_turns": 5},
    26: {"conductor_diameter_mm": 0.404, "min_bare_turns": 6},
    28: {"conductor_diameter_mm": 0.320, "min_bare_turns": 7},
    30: {"conductor_diameter_mm": 0.254, "min_bare_turns": 7},
}

# Insulated turns a wrap configuration carries, as (minimum, maximum).
INSULATED_TURN_WINDOW = {
    WRAP_MODIFIED: (0.5, 2.0),
    WRAP_CONVENTIONAL: (0.0, 0.0),
}

# Gap between two adjacent turns, as a fraction of the conductor
# diameter, and the cumulative gap allowed over one whole wrap.
MAX_SINGLE_GAP_FRACTION = 0.5
MAX_TOTAL_GAP_FRACTION = 1.0

# Levels a post may carry and where the first level starts.
MAX_LEVELS_PER_POST = 3
BASE_START_TOLERANCE_MM = 0.25

# Lengths here are sums and products of measured floats, so a wrap
# sitting exactly on a limit can land a few units in the last place
# above it. A nanometre is far below any bench measurement and absorbs
# that representation error without relaxing the limit.
LENGTH_TOLERANCE_MM = 1.0e-9

ACCEPTED = "operation-accepted"
REFUSED = "operation-refused"


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def _whole(label, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be >= %d, got %r" % (label, minimum, value))
    return value


def gauge_spec(gauge):
    """Conductor diameter and minimum bare turns for one wire gauge."""
    if not isinstance(gauge, int) or isinstance(gauge, bool):
        raise ValueError("gauge must be an integer, got %r" % (gauge,))
    if gauge not in WIRE_GAUGE_SCHEDULE:
        raise ValueError(
            "gauge %r is outside the wrapping schedule (have %s)"
            % (gauge, ", ".join(str(g) for g in sorted(WIRE_GAUGE_SCHEDULE)))
        )
    return dict(WIRE_GAUGE_SCHEDULE[gauge])


def required_bare_turns(gauge):
    """Minimum number of bare conductor turns the gauge owes."""
    return gauge_spec(gauge)["min_bare_turns"]


def insulated_turn_window(wrap_type):
    """Allowed (minimum, maximum) insulated turns for a wrap type."""
    if wrap_type not in VALID_WRAP_TYPES:
        raise ValueError(
            "wrap_type %r is unknown (expected one of %s)"
            % (wrap_type, ", ".join(VALID_WRAP_TYPES))
        )
    return INSULATED_TURN_WINDOW[wrap_type]


def single_gap_limit_mm(gauge):
    """Largest gap allowed between two adjacent turns, in millimetres."""
    return gauge_spec(gauge)["conductor_diameter_mm"] * MAX_SINGLE_GAP_FRACTION


def total_gap_limit_mm(gauge):
    """Largest cumulative gap allowed over one wrap, in millimetres."""
    return gauge_spec(gauge)["conductor_diameter_mm"] * MAX_TOTAL_GAP_FRACTION


def wrap_height_mm(gauge, bare_turns, insulated_turns, insulation_wall_mm):
    """Height one wrap occupies on the post, in millimetres."""
    conductor = gauge_spec(gauge)["conductor_diameter_mm"]
    bare = _numeric("bare_turns", bare_turns, 0.0)
    insulated = _numeric("insulated_turns", insulated_turns, 0.0)
    wall = _numeric("insulation_wall_mm", insulation_wall_mm, 0.0)
    return bare * conductor + insulated * (conductor + 2.0 * wall)


def usable_post_length_mm(post_length_mm, base_offset_mm, occupied_length_mm):
    """Post length still free for a new wrap, in millimetres."""
    post = _numeric("post_length_mm", post_length_mm)
    if post <= 0:
        raise ValueError("post_length_mm must be positive")
    offset = _numeric("base_offset_mm", base_offset_mm, 0.0)
    occupied = _numeric("occupied_length_mm", occupied_length_mm, 0.0)
    free = post - offset - occupied
    if free < 0.0:
        raise ValueError(
            "base offset and occupied length exceed the post length "
            "(%r + %r > %r)" % (offset, occupied, post)
        )
    return free


def validate_operation(record):
    """Validate one wrapping operation record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("operation must be a mapping")
    wrap_id = record.get("id")
    if not isinstance(wrap_id, str) or not wrap_id.strip():
        raise ValueError("operation needs a non-empty string id")
    gauge = record.get("gauge")
    gauge_spec(gauge)
    wrap_type = record.get("wrap_type", WRAP_MODIFIED)
    insulated_turn_window(wrap_type)
    bare_turns = _whole("operation %s bare_turns" % wrap_id, record.get("bare_turns", 0))
    insulated_turns = _numeric(
        "operation %s insulated_turns" % wrap_id, record.get("insulated_turns", 0.0), 0.0
    )
    level = _whole("operation %s level" % wrap_id, record.get("level", 1), 1)
    post_corners = _whole(
        "operation %s post_corners" % wrap_id, record.get("post_corners", 4), 3
    )
    corner_contacts = _whole(
        "operation %s corner_contacts" % wrap_id, record.get("corner_contacts", 0)
    )
    gaps = record.get("turn_gaps_mm", [])
    if not isinstance(gaps, (list, tuple)):
        raise ValueError("operation %s turn_gaps_mm must be a sequence" % wrap_id)
    gaps = [
        _numeric("operation %s turn gap" % wrap_id, g, 0.0) for g in gaps
    ]
    return {
        "id": wrap_id,
        "gauge": gauge,
        "wrap_type": wrap_type,
        "bare_turns": bare_turns,
        "insulated_turns": insulated_turns,
        "level": level,
        "post_corners": post_corners,
        "corner_contacts": corner_contacts,
        "turn_gaps_mm": gaps,
        "post_length_mm": _numeric(
            "operation %s post_length_mm" % wrap_id, record.get("post_length_mm", 12.0)
        ),
        "base_offset_mm": _numeric(
            "operation %s base_offset_mm" % wrap_id, record.get("base_offset_mm", 0.0), 0.0
        ),
        "occupied_length_mm": _numeric(
            "operation %s occupied_length_mm" % wrap_id,
            record.get("occupied_length_mm", 0.0),
            0.0,
        ),
        "start_height_mm": _numeric(
            "operation %s start_height_mm" % wrap_id, record.get("start_height_mm", 0.0), 0.0
        ),
        "insulation_wall_mm": _numeric(
            "operation %s insulation_wall_mm" % wrap_id,
            record.get("insulation_wall_mm", 0.2),
            0.0,
        ),
    }


def assess_turn_count(record):
    """Findings about the turn schedule of one operation."""
    norm = validate_operation(record)
    findings = []
    needed = required_bare_turns(norm["gauge"])
    if norm["bare_turns"] < needed:
        findings.append("bare-turn-count-below-gauge-schedule")
    low, high = insulated_turn_window(norm["wrap_type"])
    if norm["insulated_turns"] < low - LENGTH_TOLERANCE_MM:
        findings.append("insulated-turns-below-configuration-window")
    elif norm["insulated_turns"] > high + LENGTH_TOLERANCE_MM:
        findings.append("insulated-turns-above-configuration-window")
    return findings


def assess_tightness(record):
    """Findings about how tightly one wrap is laid on the post."""
    norm = validate_operation(record)
    findings = []
    expected_contacts = norm["bare_turns"] * norm["post_corners"]
    if norm["corner_contacts"] < expected_contacts:
        findings.append("turns-not-seated-on-every-post-corner")
    single_limit = single_gap_limit_mm(norm["gauge"])
    if any(g > single_limit + LENGTH_TOLERANCE_MM for g in norm["turn_gaps_mm"]):
        findings.append("single-turn-gap-above-limit")
    if sum(norm["turn_gaps_mm"]) > total_gap_limit_mm(norm["gauge"]) + LENGTH_TOLERANCE_MM:
        findings.append("cumulative-turn-gap-above-limit")
    return findings


def assess_position(record):
    """Findings about where one wrap sits on the post."""
    norm = validate_operation(record)
    findings = []
    if norm["level"] > MAX_LEVELS_PER_POST:
        findings.append("level-index-above-post-capacity")
    if norm["level"] == 1:
        if norm["start_height_mm"] > BASE_START_TOLERANCE_MM + LENGTH_TOLERANCE_MM:
            findings.append("first-level-not-started-at-post-base")
    elif norm["start_height_mm"] + LENGTH_TOLERANCE_MM < norm["occupied_length_mm"]:
        findings.append("level-started-below-the-wrap-under-it")
    free = usable_post_length_mm(
        norm["post_length_mm"], norm["base_offset_mm"], norm["occupied_length_mm"]
    )
    height = wrap_height_mm(
        norm["gauge"],
        norm["bare_turns"],
        norm["insulated_turns"],
        norm["insulation_wall_mm"],
    )
    if height > free + LENGTH_TOLERANCE_MM:
        findings.append("wrap-height-exceeds-usable-post-length")
    return findings


def assess_operation(record):
    """Assess one wrapping operation against the process rules."""
    norm = validate_operation(record)
    findings = []
    findings.extend(assess_turn_count(norm))
    findings.extend(assess_tightness(norm))
    findings.extend(assess_position(norm))
    height = wrap_height_mm(
        norm["gauge"],
        norm["bare_turns"],
        norm["insulated_turns"],
        norm["insulation_wall_mm"],
    )
    return {
        "id": norm["id"],
        "gauge": norm["gauge"],
        "wrap_type": norm["wrap_type"],
        "required_bare_turns": required_bare_turns(norm["gauge"]),
        "wrap_height_mm": height,
        "usable_post_length_mm": usable_post_length_mm(
            norm["post_length_mm"], norm["base_offset_mm"], norm["occupied_length_mm"]
        ),
        "findings": findings,
        "status": ACCEPTED if not findings else REFUSED,
        "compliant": not findings,
    }


def assess_wrapping_operations(records):
    """Run the wrapping-operation assessment over a set of wraps."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    results = []
    seen = set()
    for record in records:
        result = assess_operation(record)
        if result["id"] in seen:
            raise ValueError("duplicate operation id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    refused = [r["id"] for r in results if not r["compliant"]]
    return {
        "operations": results,
        "refused_ids": refused,
        "accepted_ids": [r["id"] for r in results if r["compliant"]],
        "compliant": not refused,
    }
