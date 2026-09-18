"""Rework and rewrap rules for a wrapping post.

Anchor: ECSS-Q-ST-70-30C, wrapping rework clauses (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Count what the post has already taken. Each removal drags the wire
   back over the corners that made the joint, so a post has a bounded
   number of rewraps in it, and the count is a property of the post
   rather than of the connection being remade.
2. Insist on the removal method. A wrap comes off with an unwrapping
   tool that unwinds it; a wrap pulled off with pliers rolls the post
   corners over and leaves nothing for the next wrap to bite on.
3. Inspect the post after the removal. Deformed or rounded corners end
   the post's usable life whatever the rewrap count says, and the
   disposition becomes replacement of the terminal.
4. Refuse the used length of wire. The removed turns are work-hardened
   and carry the impressions of the corners, so the used length is cut
   away and the new wrap is made on wire that has never been wrapped.
5. Compute the wire the new wrap needs, from the post perimeter, the
   turn count and the service loop the routing owes, and compare it
   against the length still available after the cut.
6. Return the disposition: proceed, replace the wire, or replace the
   terminal.

Every threshold is a declared project policy value the caller may
override, because the rework allowance a programme adopts belongs to
its own process specification.

Stdlib only, offline, deterministic.
"""

# Removals one post may take before it is retired, and levels the post
# may carry at any one time.
MAX_REMOVALS_PER_POST = 3
MAX_LEVELS_PER_POST = 3

REMOVAL_UNWRAPPING_TOOL = "unwrapping-tool"
REMOVAL_PULLED_OFF = "pulled-off"
REMOVAL_NONE = "none"
VALID_REMOVAL_METHODS = (
    REMOVAL_UNWRAPPING_TOOL,
    REMOVAL_PULLED_OFF,
    REMOVAL_NONE,
)

CORNERS_SHARP = "sharp"
CORNERS_ROUNDED = "rounded"
CORNERS_DEFORMED = "deformed"
VALID_CORNER_STATES = (CORNERS_SHARP, CORNERS_ROUNDED, CORNERS_DEFORMED)

# Conductor diameter per gauge, in millimetres, and the minimum bare
# turns the gauge owes. Used to size the wire a new wrap consumes.
CONDUCTOR_DIAMETER_MM = {
    20: 0.813,
    22: 0.643,
    24: 0.511,
    26: 0.404,
    28: 0.320,
    30: 0.254,
}
MIN_BARE_TURNS = {20: 4, 22: 5, 24: 5, 26: 6, 28: 7, 30: 7}

# Allowance on the wrapped length for the wire climbing the post, and
# the strip length left beyond the last turn.
WRAP_LENGTH_ALLOWANCE = 0.10
END_STRIP_ALLOWANCE_MM = 3.0

PROCEED = "rewrap-permitted"
REPLACE_WIRE = "rewrap-blocked-replace-wire"
REPLACE_TERMINAL = "rewrap-blocked-replace-terminal"

# Lengths are sums of measured floats, so a wire that is exactly long
# enough can land a few units in the last place short. A nanometre is
# far below any bench measurement and absorbs that representation error
# without relaxing the requirement.
LENGTH_TOLERANCE_MM = 1.0e-9


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


def _boolean(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def conductor_diameter_mm(gauge):
    """Conductor diameter for one wire gauge, in millimetres."""
    if not isinstance(gauge, int) or isinstance(gauge, bool):
        raise ValueError("gauge must be an integer, got %r" % (gauge,))
    if gauge not in CONDUCTOR_DIAMETER_MM:
        raise ValueError(
            "gauge %r is outside the rework schedule (have %s)"
            % (gauge, ", ".join(str(g) for g in sorted(CONDUCTOR_DIAMETER_MM)))
        )
    return CONDUCTOR_DIAMETER_MM[gauge]


def minimum_bare_turns(gauge):
    """Minimum bare turns a wrap of this gauge owes."""
    conductor_diameter_mm(gauge)
    return MIN_BARE_TURNS[gauge]


def post_perimeter_mm(post_width_mm, post_thickness_mm):
    """Perimeter of one turn around a rectangular post, in millimetres."""
    width = _numeric("post_width_mm", post_width_mm)
    thickness = _numeric("post_thickness_mm", post_thickness_mm)
    if width <= 0 or thickness <= 0:
        raise ValueError("post cross-section dimensions must be positive")
    return 2.0 * (width + thickness)


def wire_length_required_mm(gauge, turns, post_width_mm, post_thickness_mm,
                            service_loop_mm=0.0):
    """Wire one new wrap consumes, in millimetres."""
    conductor_diameter_mm(gauge)
    count = _whole("turns", turns, 1)
    loop = _numeric("service_loop_mm", service_loop_mm, 0.0)
    perimeter = post_perimeter_mm(post_width_mm, post_thickness_mm)
    wrapped = count * perimeter * (1.0 + WRAP_LENGTH_ALLOWANCE)
    return wrapped + END_STRIP_ALLOWANCE_MM + loop


def removals_remaining(previous_removals):
    """Removals the post has left before it is retired."""
    used = _whole("previous_removals", previous_removals, 0)
    return max(0, MAX_REMOVALS_PER_POST - used)


def validate_rework(record):
    """Validate one rework record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("rework record must be a mapping")
    post_id = record.get("post_id")
    if not isinstance(post_id, str) or not post_id.strip():
        raise ValueError("rework record needs a non-empty string post_id")
    gauge = record.get("gauge")
    conductor_diameter_mm(gauge)
    method = record.get("removal_method", REMOVAL_UNWRAPPING_TOOL)
    if method not in VALID_REMOVAL_METHODS:
        raise ValueError(
            "post %s removal_method %r is unknown (expected one of %s)"
            % (post_id, method, ", ".join(VALID_REMOVAL_METHODS))
        )
    corners = record.get("corner_state", CORNERS_SHARP)
    if corners not in VALID_CORNER_STATES:
        raise ValueError(
            "post %s corner_state %r is unknown (expected one of %s)"
            % (post_id, corners, ", ".join(VALID_CORNER_STATES))
        )
    turns = record.get("planned_turns")
    if turns is None:
        turns = MIN_BARE_TURNS[gauge]
    return {
        "post_id": post_id,
        "gauge": gauge,
        "previous_removals": _whole(
            "post %s previous_removals" % post_id, record.get("previous_removals", 0)
        ),
        "levels_in_place": _whole(
            "post %s levels_in_place" % post_id, record.get("levels_in_place", 0)
        ),
        "removal_method": method,
        "corner_state": corners,
        "used_length_cut_off": _boolean(
            "post %s used_length_cut_off" % post_id,
            record.get("used_length_cut_off", False),
        ),
        "planned_turns": _whole("post %s planned_turns" % post_id, turns, 1),
        "post_width_mm": _numeric(
            "post %s post_width_mm" % post_id, record.get("post_width_mm", 0.64)
        ),
        "post_thickness_mm": _numeric(
            "post %s post_thickness_mm" % post_id, record.get("post_thickness_mm", 0.64)
        ),
        "available_wire_mm": _numeric(
            "post %s available_wire_mm" % post_id, record.get("available_wire_mm", 0.0), 0.0
        ),
        "service_loop_mm": _numeric(
            "post %s service_loop_mm" % post_id, record.get("service_loop_mm", 0.0), 0.0
        ),
    }


def assess_post_condition(record):
    """Findings about whether the post itself survives the rework."""
    norm = validate_rework(record)
    findings = []
    if norm["corner_state"] == CORNERS_DEFORMED:
        findings.append("post-corners-deformed-by-removal")
    elif norm["corner_state"] == CORNERS_ROUNDED:
        findings.append("post-corners-rounded-by-removal")
    if removals_remaining(norm["previous_removals"]) == 0:
        findings.append("post-rewrap-allowance-exhausted")
    if norm["levels_in_place"] >= MAX_LEVELS_PER_POST:
        findings.append("post-levels-already-at-capacity")
    return findings


def assess_removal_method(record):
    """Findings about how the previous wrap was taken off."""
    norm = validate_rework(record)
    findings = []
    if norm["removal_method"] == REMOVAL_PULLED_OFF:
        findings.append("wrap-pulled-off-instead-of-unwound")
    elif norm["removal_method"] == REMOVAL_NONE:
        findings.append("no-removal-method-on-record")
    return findings


def assess_wire_length(record):
    """Findings about the wire left for the new wrap, plus the two lengths."""
    norm = validate_rework(record)
    findings = []
    if not norm["used_length_cut_off"]:
        findings.append("used-wire-length-not-cut-away")
    needed = wire_length_required_mm(
        norm["gauge"],
        norm["planned_turns"],
        norm["post_width_mm"],
        norm["post_thickness_mm"],
        norm["service_loop_mm"],
    )
    if norm["available_wire_mm"] + LENGTH_TOLERANCE_MM < needed:
        findings.append("remaining-wire-too-short-for-a-new-wrap")
    return findings, needed


def assess_rework(record):
    """Assess one post against the rework and rewrap rules."""
    norm = validate_rework(record)
    post_findings = assess_post_condition(norm)
    method_findings = assess_removal_method(norm)
    wire_findings, needed = assess_wire_length(norm)
    findings = post_findings + method_findings + wire_findings
    if post_findings:
        disposition = REPLACE_TERMINAL
    elif wire_findings or method_findings:
        disposition = REPLACE_WIRE
    else:
        disposition = PROCEED
    if norm["planned_turns"] < minimum_bare_turns(norm["gauge"]):
        findings.append("planned-turns-below-gauge-schedule")
        if disposition == PROCEED:
            disposition = REPLACE_WIRE
    return {
        "post_id": norm["post_id"],
        "gauge": norm["gauge"],
        "removals_remaining": removals_remaining(norm["previous_removals"]),
        "wire_required_mm": needed,
        "wire_available_mm": norm["available_wire_mm"],
        "findings": findings,
        "disposition": disposition,
        "permitted": disposition == PROCEED,
    }


def assess_rework_campaign(records):
    """Run the rework assessment over a set of posts."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    results = []
    seen = set()
    for record in records:
        result = assess_rework(record)
        if result["post_id"] in seen:
            raise ValueError("duplicate post id %r" % (result["post_id"],))
        seen.add(result["post_id"])
        results.append(result)
    return {
        "posts": results,
        "permitted_ids": [r["post_id"] for r in results if r["permitted"]],
        "replace_wire_ids": [
            r["post_id"] for r in results if r["disposition"] == REPLACE_WIRE
        ],
        "replace_terminal_ids": [
            r["post_id"] for r in results if r["disposition"] == REPLACE_TERMINAL
        ],
        "all_permitted": all(r["permitted"] for r in results),
    }
