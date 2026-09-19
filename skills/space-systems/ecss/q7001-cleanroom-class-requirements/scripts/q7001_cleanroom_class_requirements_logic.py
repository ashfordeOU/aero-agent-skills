"""Choosing and grading an airborne particulate class for an operation.

Anchor: the clean-area provisions of the contamination and cleanliness
control practice of ECSS-Q-ST-70-01C, which designate airborne classes
by the ISO 14644-1 scheme (paraphrased into an implementable procedure;
no standard text is reproduced).

Procedure implemented here:

1. An airborne class is a concentration ceiling that depends on the
   particle size you ask about. The class-designation relation gives the
   maximum number of particles of at least the threshold size per cubic
   metre for an integer or decimal class designation, and the ceiling
   grows steeply as the threshold size falls.
2. Selecting a class for an operation runs the relation backwards. The
   operation states the concentration it can tolerate at a threshold
   size; the answer is the least demanding class that still sits under
   that ceiling, because every class cleaner than that is money and
   schedule spent on air the hardware does not need.
3. The relation is only meaningful over the particle-size range the
   scheme covers. A threshold outside it is refused rather than
   extrapolated, because the extrapolated ceiling is not a class at all.
4. An area is graded against the requirement, not merely reported. An
   area looser than the operation needs fails. An area two or more
   classes cleaner than the operation needs passes, and is reported,
   because it is usually a scheduling mistake: the scarce clean space is
   being spent on work that did not need it.
5. Classes are demonstrated in a state. A requirement written for work
   in progress is not met by a demonstration taken with nobody in the
   room, so an operational requirement backed only by an at-rest or
   as-built demonstration is a finding.

Stdlib only, offline, deterministic.
"""

# The class-designation relation: ceiling = 10**class * (SIZE_REFERENCE_UM /
# size)**SIZE_EXPONENT particles of at least `size` per cubic metre.
SIZE_REFERENCE_UM = 0.1
SIZE_EXPONENT = 2.08

# The particle-size range over which the relation designates a class.
MIN_THRESHOLD_UM = 0.1
MAX_THRESHOLD_UM = 5.0

# Integer class designations available for selection.
MIN_CLASS = 1
MAX_CLASS = 9

# Occupancy states a demonstration can have been taken in, cleanest
# (emptiest) first. An operational requirement is met only by an
# operational demonstration.
STATE_AS_BUILT = "as-built"
STATE_AT_REST = "at-rest"
STATE_OPERATIONAL = "operational"
OCCUPANCY_STATES = (STATE_AS_BUILT, STATE_AT_REST, STATE_OPERATIONAL)

# The ceiling is a power expression, so a requirement written exactly on
# a class ceiling can land a unit in the last place either side of it.
# This tolerance absorbs that representation error only.
RELATIVE_TOLERANCE = 1.0e-9

# An area this much cleaner than the work needs is reported as overspend.
OVERSPECIFICATION_MARGIN_CLASSES = 2


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return " ".join(value.split())


def _positive(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return float(value)


def validate_threshold_um(size_um):
    """Return the threshold particle size, refusing one outside the range."""
    size = _positive("threshold particle size", size_um)
    if size < MIN_THRESHOLD_UM * (1.0 - RELATIVE_TOLERANCE):
        raise ValueError(
            "threshold particle size %r um is below %r um, where the "
            "class-designation relation designates no class" % (size_um, MIN_THRESHOLD_UM)
        )
    if size > MAX_THRESHOLD_UM * (1.0 + RELATIVE_TOLERANCE):
        raise ValueError(
            "threshold particle size %r um is above %r um, where the "
            "class-designation relation designates no class" % (size_um, MAX_THRESHOLD_UM)
        )
    return size


def validate_class_number(iso_class):
    """Return the class designation, refusing one outside the scheme."""
    if not isinstance(iso_class, (int, float)) or isinstance(iso_class, bool):
        raise ValueError("class designation must be numeric, got %r" % (iso_class,))
    value = float(iso_class)
    if value < MIN_CLASS or value > MAX_CLASS:
        raise ValueError(
            "class designation %r lies outside %d..%d" % (iso_class, MIN_CLASS, MAX_CLASS)
        )
    return value


def class_ceiling_per_m3(iso_class, threshold_um):
    """Maximum particles of at least threshold_um per cubic metre for a class."""
    value = validate_class_number(iso_class)
    size = validate_threshold_um(threshold_um)
    return (10.0 ** value) * ((SIZE_REFERENCE_UM / size) ** SIZE_EXPONENT)


def round_to_significant(value, digits=3):
    """Round a ceiling to the reporting precision the scheme uses."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("value must be numeric, got %r" % (value,))
    if not isinstance(digits, int) or isinstance(digits, bool) or digits < 1:
        raise ValueError("digits must be a positive integer, got %r" % (digits,))
    if value == 0:
        return 0.0
    magnitude = abs(float(value))
    # Scale by repeated multiplication and division rather than a power
    # expression, and undo it the same way: a power expression is not
    # correctly rounded and does not agree across platforms.
    down = 0
    up = 0
    while magnitude >= 10.0:
        magnitude /= 10.0
        down += 1
    while magnitude < 1.0:
        magnitude *= 10.0
        up += 1
    scaled = round(magnitude, digits - 1)
    for _ in range(down):
        scaled *= 10.0
    for _ in range(up):
        scaled /= 10.0
    return scaled if value > 0 else -scaled


def required_class(tolerable_per_m3, threshold_um):
    """Least demanding integer class whose ceiling sits under the tolerance."""
    tolerable = _positive("tolerable concentration", tolerable_per_m3)
    size = validate_threshold_um(threshold_um)
    for candidate in range(MAX_CLASS, MIN_CLASS - 1, -1):
        ceiling = class_ceiling_per_m3(candidate, size)
        if ceiling <= tolerable * (1.0 + RELATIVE_TOLERANCE):
            return candidate
    raise ValueError(
        "no class in %d..%d holds %r particles of at least %r um per cubic "
        "metre; the operation needs a local enclosure, not a room class"
        % (MIN_CLASS, MAX_CLASS, tolerable_per_m3, threshold_um)
    )


def validate_operation(operation):
    """Validate one operation and the clean area it has been given."""
    if not isinstance(operation, dict):
        raise ValueError("operation must be a mapping")
    oid = _text("operation id", operation.get("id"))
    size = validate_threshold_um(operation.get("threshold_um", 0.5))
    tolerable = _positive(
        "operation %s tolerable_per_m3" % oid, operation.get("tolerable_per_m3")
    )
    assigned = operation.get("assigned_class")
    if assigned is None:
        raise ValueError("operation %s names no assigned_class" % oid)
    assigned = validate_class_number(assigned)
    if abs(assigned - round(assigned)) > 0.0:
        raise ValueError(
            "operation %s is assigned class %r; an area is designated at an "
            "integer class for assignment" % (oid, operation.get("assigned_class"))
        )
    state = _text(
        "operation %s demonstrated_state" % oid,
        operation.get("demonstrated_state", STATE_OPERATIONAL),
    )
    if state not in OCCUPANCY_STATES:
        raise ValueError(
            "operation %s declares state %r, which is not one of %r"
            % (oid, state, list(OCCUPANCY_STATES))
        )
    needs_operational = operation.get("hardware_exposed", True)
    if not isinstance(needs_operational, bool):
        raise ValueError("operation %s hardware_exposed must be a boolean" % oid)
    return {
        "id": oid,
        "threshold_um": size,
        "tolerable_per_m3": tolerable,
        "assigned_class": int(round(assigned)),
        "demonstrated_state": state,
        "hardware_exposed": needs_operational,
    }


def assess_operation(operation):
    """Grade one operation's assigned clean area against the class it needs."""
    norm = validate_operation(operation)
    needed = required_class(norm["tolerable_per_m3"], norm["threshold_um"])
    assigned = norm["assigned_class"]
    ceiling = class_ceiling_per_m3(assigned, norm["threshold_um"])
    findings = []
    if assigned > needed:
        findings.append("assigned-area-looser-than-the-operation-needs")
    if needed - assigned >= OVERSPECIFICATION_MARGIN_CLASSES:
        findings.append("assigned-area-far-cleaner-than-the-operation-needs")
    if norm["hardware_exposed"] and norm["demonstrated_state"] != STATE_OPERATIONAL:
        findings.append("class-demonstrated-only-with-the-room-unoccupied")
    return {
        "id": norm["id"],
        "threshold_um": norm["threshold_um"],
        "tolerable_per_m3": norm["tolerable_per_m3"],
        "required_class": needed,
        "assigned_class": assigned,
        "assigned_ceiling_per_m3": ceiling,
        "reported_ceiling_per_m3": round_to_significant(ceiling),
        "headroom_fraction": ceiling / norm["tolerable_per_m3"],
        "class_margin": needed - assigned,
        "demonstrated_state": norm["demonstrated_state"],
        "findings": findings,
        "acceptable": "assigned-area-looser-than-the-operation-needs" not in findings
        and "class-demonstrated-only-with-the-room-unoccupied" not in findings,
    }


def assess_facility_plan(operations):
    """Grade every operation in a facility plan and roll the findings up."""
    if not isinstance(operations, list) or not operations:
        raise ValueError("operations must be a non-empty list")
    rows = []
    findings = []
    seen = set()
    for operation in operations:
        row = assess_operation(operation)
        if row["id"] in seen:
            raise ValueError("duplicate operation id %r" % (row["id"],))
        seen.add(row["id"])
        findings.extend(row["findings"])
        rows.append(row)
    unacceptable = [row["id"] for row in rows if not row["acceptable"]]
    cleanest_needed = min(row["required_class"] for row in rows)
    return {
        "operation_count": len(rows),
        "operations": rows,
        "cleanest_class_required": cleanest_needed,
        "unacceptable_operation_ids": unacceptable,
        "findings": findings,
        "verdict": "clean-area-plan-acceptable"
        if not unacceptable
        else "clean-area-plan-rejected",
        "clear": not findings,
    }
