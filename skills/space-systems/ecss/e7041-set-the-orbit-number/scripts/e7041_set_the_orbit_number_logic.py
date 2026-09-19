"""Effect of setting the on-board orbit number.

Anchor: ECSS-E-ST-70-41C clause 6.22.6.4 (set the orbit number). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the commanded orbit number against the width of the on-board
   orbit number field.
2. Measure the jump the command makes against the orbit number currently
   held, forward or backward, and name it.
3. Re-evaluate every position-based activity against the new orbit position:
   those the change has carried past, those now standing at the position,
   and those still ahead.
4. Apply the declared disposition to the activities the jump carried past
   without releasing them.
5. Report the new orbit position, the grouped activities and the findings the
   change earned.
"""

__all__ = [
    "DEGREES_PER_REVOLUTION",
    "MAX_ORBIT_NUMBER_BITS",
    "JUMP_NONE",
    "JUMP_FORWARD",
    "JUMP_BACKWARD",
    "SKIPPED_DISCARD",
    "SKIPPED_KEEP",
    "SKIPPED_DISPOSITIONS",
    "orbit_number_ceiling",
    "validate_orbit_number",
    "jump_direction",
    "jump_magnitude",
    "group_activities_against_position",
    "apply_set_orbit_number",
]

DEGREES_PER_REVOLUTION = 360.0

# Widest orbit number field this model will accept.
MAX_ORBIT_NUMBER_BITS = 32

JUMP_NONE = "none"
JUMP_FORWARD = "forward"
JUMP_BACKWARD = "backward"

# What becomes of an activity the new orbit number has carried past.
SKIPPED_DISCARD = "discard"
SKIPPED_KEEP = "keep"
SKIPPED_DISPOSITIONS = (SKIPPED_DISCARD, SKIPPED_KEEP)


def _require_non_negative_int(value, label):
    """Return value as a non-negative whole count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _require_positive_int(value, label):
    """Return value as a positive whole count."""
    value = _require_non_negative_int(value, label)
    if value == 0:
        raise ValueError("%s must be positive, got 0" % label)
    return value


def _require_angle(value, label):
    """Return an ascending-node angle inside one revolution."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    angle = float(value)
    if angle != angle or angle in (float("inf"), float("-inf")):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if angle < 0.0 or angle >= DEGREES_PER_REVOLUTION:
        raise ValueError(
            "%s %r falls outside one revolution from the ascending node"
            % (label, value)
        )
    return angle


def orbit_number_ceiling(orbit_number_bits):
    """Return how many distinct orbit numbers a field of this width holds."""
    bits = _require_positive_int(orbit_number_bits, "orbit_number_bits")
    if bits > MAX_ORBIT_NUMBER_BITS:
        raise ValueError(
            "orbit_number_bits %d exceeds the %d bit model limit"
            % (bits, MAX_ORBIT_NUMBER_BITS)
        )
    return 1 << bits


def validate_orbit_number(orbit_number, orbit_number_bits):
    """Return the orbit number after checking it fits the on-board field."""
    ceiling = orbit_number_ceiling(orbit_number_bits)
    value = _require_non_negative_int(orbit_number, "orbit_number")
    if value >= ceiling:
        raise ValueError(
            "orbit_number %d does not fit a %d bit orbit number field"
            % (value, orbit_number_bits)
        )
    return value


def jump_direction(current_orbit, new_orbit):
    """Return whether the command moves the counter forward, back or nowhere."""
    if new_orbit == current_orbit:
        return JUMP_NONE
    return JUMP_FORWARD if new_orbit > current_orbit else JUMP_BACKWARD


def jump_magnitude(current_orbit, new_orbit):
    """Return how many orbits the command moves the counter by."""
    return abs(new_orbit - current_orbit)


def _normalise_activity(activity, index, orbit_number_bits):
    """Return one scheduled activity as a validated dict."""
    if not isinstance(activity, dict):
        raise ValueError("activity %d must be a mapping, got %r" % (index, activity))
    for key in ("request_id", "orbit_number", "angle_degrees"):
        if key not in activity:
            raise ValueError("activity %d missing required key '%s'" % (index, key))
    request_id = activity["request_id"]
    if not isinstance(request_id, str) or not request_id.strip():
        raise ValueError("activity %d request_id must be a non-empty string" % index)
    return {
        "request_id": request_id.strip(),
        "orbit_number": validate_orbit_number(
            activity["orbit_number"], orbit_number_bits
        ),
        "angle_degrees": _require_angle(
            activity["angle_degrees"], "activity %d angle_degrees" % index
        ),
    }


def group_activities_against_position(activities, orbit_number, angle_degrees,
                                      orbit_number_bits=16):
    """Group scheduled activities against an orbit position.

    Returns a dict of 'past', 'due' and 'ahead' tuples of request identifiers.
    """
    if not isinstance(activities, (list, tuple)):
        raise ValueError("activities must be a list or tuple")
    orbit = validate_orbit_number(orbit_number, orbit_number_bits)
    angle = _require_angle(angle_degrees, "angle_degrees")
    mark = orbit * DEGREES_PER_REVOLUTION + angle

    loaded = [
        _normalise_activity(item, i, orbit_number_bits)
        for i, item in enumerate(activities)
    ]
    seen = set()
    for item in loaded:
        if item["request_id"] in seen:
            raise ValueError(
                "request identifier '%s' appears more than once" % item["request_id"]
            )
        seen.add(item["request_id"])

    past = []
    due = []
    ahead = []
    for item in sorted(
        loaded,
        key=lambda a: (
            a["orbit_number"] * DEGREES_PER_REVOLUTION + a["angle_degrees"],
            a["request_id"],
        ),
    ):
        key = item["orbit_number"] * DEGREES_PER_REVOLUTION + item["angle_degrees"]
        if item["orbit_number"] == orbit and abs(item["angle_degrees"] - angle) <= 1e-9:
            due.append(item["request_id"])
        elif key < mark:
            past.append(item["request_id"])
        else:
            ahead.append(item["request_id"])
    return {"past": tuple(past), "due": tuple(due), "ahead": tuple(ahead)}


def apply_set_orbit_number(spec):
    """Assess a clause 6.22.6.4 set orbit number command.

    spec keys: current_orbit_number, new_orbit_number, angle_degrees,
    activities, orbit_number_bits, and the optional skipped_disposition of
    'discard' or 'keep'.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "current_orbit_number",
        "new_orbit_number",
        "angle_degrees",
        "activities",
        "orbit_number_bits",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    disposition = spec.get("skipped_disposition", SKIPPED_DISCARD)
    if disposition not in SKIPPED_DISPOSITIONS:
        raise ValueError(
            "skipped_disposition %r is not one of %s"
            % (disposition, ", ".join(SKIPPED_DISPOSITIONS))
        )

    bits = spec["orbit_number_bits"]
    current = validate_orbit_number(spec["current_orbit_number"], bits)
    new_orbit = validate_orbit_number(spec["new_orbit_number"], bits)
    angle = _require_angle(spec["angle_degrees"], "angle_degrees")

    before = group_activities_against_position(
        spec["activities"], current, angle, bits
    )
    after = group_activities_against_position(
        spec["activities"], new_orbit, angle, bits
    )

    direction = jump_direction(current, new_orbit)
    magnitude = jump_magnitude(current, new_orbit)

    newly_past = tuple(
        request_id
        for request_id in after["past"]
        if request_id not in set(before["past"]) and request_id not in set(before["due"])
    )
    newly_ahead = tuple(
        request_id
        for request_id in after["ahead"]
        if request_id in set(before["past"]) or request_id in set(before["due"])
    )

    findings = []
    if direction == JUMP_BACKWARD:
        findings.append(
            "the orbit number moves back by %d orbits; %d activities return to the "
            "future of the schedule" % (magnitude, len(newly_ahead))
        )
    if newly_past:
        findings.append(
            "%d activities are skipped by the change without being released: %s"
            % (len(newly_past), ", ".join(sorted(newly_past)))
        )
    if direction == JUMP_NONE:
        findings.append(
            "the commanded orbit number equals the one held; the schedule is "
            "unchanged"
        )

    if disposition == SKIPPED_DISCARD:
        retained = tuple(
            request_id
            for request_id in after["due"] + after["ahead"]
        )
    else:
        retained = tuple(
            request_id
            for request_id in after["past"] + after["due"] + after["ahead"]
        )

    return {
        "current_orbit_number": current,
        "new_orbit_number": new_orbit,
        "angle_degrees": angle,
        "jump_direction": direction,
        "jump_magnitude": magnitude,
        "past_activities": after["past"],
        "due_activities": after["due"],
        "ahead_activities": after["ahead"],
        "newly_skipped": newly_past,
        "returned_to_future": newly_ahead,
        "skipped_disposition": disposition,
        "retained_activities": tuple(sorted(retained)),
        "accepted": not newly_past and direction != JUMP_BACKWARD,
        "findings": findings,
    }
