"""Thread forming control for threaded fasteners: rolled versus cut.

Anchor: ECSS-Q-ST-70-46, manufacturing clause, thread forming
(paraphrased into an implementable procedure; no standard text is
reproduced).

Procedure implemented here:

1. A thread is made one of two ways and they are not equivalent.
   Cutting removes metal and leaves the grain severed at the root;
   rolling displaces metal and leaves the grain following the profile
   with a compressive residual stress in the root. The root is where
   a fastener fails in fatigue, so the forming method is a strength
   decision and not a shop-convenience one.
2. The method is forced by the property class and the duty. At or
   above the rolled-thread class floor, or on any fatigue-critical
   part, the thread is rolled. Below both, cutting is permitted.
3. Where the part is also heat treated, the sequence matters as much
   as the method. Rolling after heat treatment leaves the compressive
   residual stress in the finished part; rolling before it lets the
   austenitizing soak relax most of that stress away. The high
   classes and the fatigue-critical parts roll after.
4. The geometry follows from the thread designation, not from a
   table lookup: the pitch diameter and the minor diameter come from
   the nominal diameter and the pitch, the rolling blank sits just
   above the pitch diameter because the displaced metal has to fill
   the crest, and the root radius has a floor below which the root is
   a notch whatever the method.
5. The fatigue allowable earned by the method and sequence is a
   factor on the base allowable, and it is compared against the duty
   load rather than asserted. A part that needs a rolled-after-heat-
   treatment thread and has a cut one fails that comparison instead
   of merely being irregular.

Stdlib only, offline, deterministic.
"""

ROLLED = "rolled"
CUT = "cut"

ROLL_AFTER_HEAT_TREATMENT = "roll-after-heat-treatment"
ROLL_BEFORE_HEAT_TREATMENT = "roll-before-heat-treatment"
NOT_APPLICABLE = "not-applicable"

ACCEPTED = "accepted"
ACCEPTED_WITH_CONTROLS = "accepted-with-controls"
REJECTED = "rejected"

_RANK = {ACCEPTED: 0, ACCEPTED_WITH_CONTROLS: 1, REJECTED: 2}

# ISO metric property classes admitted here, in ascending strength.
VALID_PROPERTY_CLASSES = ("4.6", "4.8", "5.8", "6.8", "8.8", "9.8", "10.9", "12.9")

# At or above this class the thread is rolled rather than cut.
ROLLED_THREAD_CLASS_FLOOR = "8.8"

# At or above this class a rolled thread is formed after heat treatment.
ROLL_AFTER_CLASS_FLOOR = "10.9"

# Profile constants of the ISO metric thread form, as fractions of the
# pitch. They are geometry, derived from the 60 degree triangle.
PITCH_DIAMETER_OFFSET = 0.649519052838329
MINOR_DIAMETER_OFFSET = 1.226869322243816
ROOT_RADIUS_FLOOR_FRACTION = 0.125

# Fatigue allowable earned by the forming method and sequence.
FATIGUE_BENEFIT_FACTOR = {
    (ROLLED, ROLL_AFTER_HEAT_TREATMENT): 1.30,
    (ROLLED, ROLL_BEFORE_HEAT_TREATMENT): 1.10,
    (ROLLED, NOT_APPLICABLE): 1.15,
    (CUT, NOT_APPLICABLE): 1.00,
    (CUT, ROLL_AFTER_HEAT_TREATMENT): 1.00,
    (CUT, ROLL_BEFORE_HEAT_TREATMENT): 1.00,
}

# Fraction of the pitch the blank sits above the pitch diameter so the
# displaced metal fills the crest.
DEFAULT_FILL_ALLOWANCE_FRACTION = 0.02

# Diameters and factors are products and quotients of measured floats,
# so a case exactly on a bound can land a few units in the last place
# outside it. These absorb that without moving a bound.
LENGTH_TOLERANCE_MM = 1.0e-9
FACTOR_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def class_rank(property_class):
    """Position of an admitted property class in ascending strength."""
    if not isinstance(property_class, str) or property_class not in VALID_PROPERTY_CLASSES:
        raise ValueError(
            "unknown property class %r (expected one of %s)"
            % (property_class, ", ".join(VALID_PROPERTY_CLASSES))
        )
    return VALID_PROPERTY_CLASSES.index(property_class)


def _validate_thread(nominal_diameter_mm, pitch_mm):
    diameter = _numeric("nominal_diameter_mm", nominal_diameter_mm, 0.0)
    pitch = _numeric("pitch_mm", pitch_mm, 0.0)
    if diameter <= 0.0:
        raise ValueError("nominal_diameter_mm must be positive")
    if pitch <= 0.0:
        raise ValueError("pitch_mm must be positive")
    if pitch >= diameter:
        raise ValueError("pitch_mm must sit below nominal_diameter_mm")
    return diameter, pitch


def pitch_diameter_mm(nominal_diameter_mm, pitch_mm):
    """Pitch diameter of an external metric thread, in millimetres."""
    diameter, pitch = _validate_thread(nominal_diameter_mm, pitch_mm)
    return diameter - PITCH_DIAMETER_OFFSET * pitch


def minor_diameter_mm(nominal_diameter_mm, pitch_mm):
    """Minor diameter of an external metric thread, in millimetres."""
    diameter, pitch = _validate_thread(nominal_diameter_mm, pitch_mm)
    return diameter - MINOR_DIAMETER_OFFSET * pitch


def minimum_root_radius_mm(pitch_mm):
    """Root radius floor below which the root behaves as a notch."""
    pitch = _numeric("pitch_mm", pitch_mm, 0.0)
    if pitch <= 0.0:
        raise ValueError("pitch_mm must be positive")
    return ROOT_RADIUS_FLOOR_FRACTION * pitch


def root_radius_admissible(root_radius_mm, pitch_mm):
    """Whether a measured root radius clears the floor for its pitch."""
    radius = _numeric("root_radius_mm", root_radius_mm, 0.0)
    floor = minimum_root_radius_mm(pitch_mm)
    return radius >= floor - LENGTH_TOLERANCE_MM


def rolling_blank_diameter_mm(
    nominal_diameter_mm, pitch_mm, fill_allowance_fraction=DEFAULT_FILL_ALLOWANCE_FRACTION
):
    """Blank diameter a rolled thread is formed from, in millimetres."""
    diameter, pitch = _validate_thread(nominal_diameter_mm, pitch_mm)
    fraction = _numeric("fill_allowance_fraction", fill_allowance_fraction, 0.0)
    if fraction > 0.25:
        raise ValueError("fill_allowance_fraction must not exceed 0.25 of the pitch")
    blank = pitch_diameter_mm(diameter, pitch) + fraction * pitch
    floor = minor_diameter_mm(diameter, pitch)
    if not floor - LENGTH_TOLERANCE_MM <= blank <= diameter + LENGTH_TOLERANCE_MM:
        raise ValueError("blank diameter falls outside the minor-to-nominal band")
    return blank


def required_forming_method(property_class, fatigue_critical=False):
    """Forming method the class and duty force on the thread."""
    rank = class_rank(property_class)
    if fatigue_critical or rank >= class_rank(ROLLED_THREAD_CLASS_FLOOR):
        return ROLLED
    return CUT


def required_forming_sequence(property_class, fatigue_critical=False, heat_treated=True):
    """Forming sequence relative to heat treatment."""
    if not heat_treated:
        return NOT_APPLICABLE
    rank = class_rank(property_class)
    if fatigue_critical or rank >= class_rank(ROLL_AFTER_CLASS_FLOOR):
        return ROLL_AFTER_HEAT_TREATMENT
    return ROLL_BEFORE_HEAT_TREATMENT


def fatigue_benefit_factor(method, sequence):
    """Fatigue allowable factor earned by a method and sequence pair."""
    key = (method, sequence)
    if key not in FATIGUE_BENEFIT_FACTOR:
        raise ValueError("unknown method and sequence pair %r" % (key,))
    return FATIGUE_BENEFIT_FACTOR[key]


def fatigue_allowable_n(base_allowable_n, method, sequence):
    """Fatigue allowable a formed thread earns, in newtons."""
    base = _numeric("base_allowable_n", base_allowable_n, 0.0)
    if base <= 0.0:
        raise ValueError("base_allowable_n must be positive")
    return base * fatigue_benefit_factor(method, sequence)


def validate_thread_record(record):
    """Validate one thread-forming record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("thread record must be a mapping")
    part = record.get("part_number")
    if not isinstance(part, str) or not part.strip():
        raise ValueError("thread record needs a non-empty part_number")
    property_class = record.get("property_class")
    class_rank(property_class)
    method = record.get("declared_method")
    if method not in (ROLLED, CUT):
        raise ValueError("declared_method must be %r or %r" % (ROLLED, CUT))
    sequence = record.get(
        "declared_sequence", NOT_APPLICABLE
    )
    if sequence not in (
        ROLL_AFTER_HEAT_TREATMENT,
        ROLL_BEFORE_HEAT_TREATMENT,
        NOT_APPLICABLE,
    ):
        raise ValueError("unknown declared_sequence %r" % (sequence,))
    diameter, pitch = _validate_thread(
        record.get("nominal_diameter_mm"), record.get("pitch_mm")
    )
    return {
        "part_number": part.strip(),
        "property_class": property_class,
        "declared_method": method,
        "declared_sequence": sequence,
        "nominal_diameter_mm": diameter,
        "pitch_mm": pitch,
        "root_radius_mm": _numeric(
            "root_radius_mm",
            record.get("root_radius_mm", ROOT_RADIUS_FLOOR_FRACTION * pitch),
            0.0,
        ),
        "fatigue_critical": bool(record.get("fatigue_critical", False)),
        "heat_treated": bool(record.get("heat_treated", True)),
        "base_fatigue_allowable_n": _numeric(
            "base_fatigue_allowable_n",
            record.get("base_fatigue_allowable_n", 10000.0),
            0.0,
        ),
        "duty_load_n": _numeric("duty_load_n", record.get("duty_load_n", 0.0), 0.0),
    }


def assess_thread_forming(record):
    """Assess one thread-forming declaration end to end."""
    norm = validate_thread_record(record)
    findings = []
    controls = []
    disposition = ACCEPTED

    def escalate(level):
        if _RANK[level] > _RANK[disposition]:
            return level
        return disposition

    required_method = required_forming_method(
        norm["property_class"], norm["fatigue_critical"]
    )
    required_sequence = required_forming_sequence(
        norm["property_class"], norm["fatigue_critical"], norm["heat_treated"]
    )
    if required_method == ROLLED and norm["declared_method"] == CUT:
        findings.append("cut-thread-where-a-rolled-thread-is-required")
        disposition = escalate(REJECTED)
    if (
        norm["declared_method"] == ROLLED
        and required_sequence == ROLL_AFTER_HEAT_TREATMENT
        and norm["declared_sequence"] != ROLL_AFTER_HEAT_TREATMENT
    ):
        findings.append("thread-rolled-before-the-heat-treatment-that-relaxes-it")
        disposition = escalate(REJECTED)
    if (
        norm["declared_method"] == ROLLED
        and norm["declared_sequence"] == ROLL_AFTER_HEAT_TREATMENT
    ):
        controls.append("confirm-the-rolling-machine-capability-on-hardened-stock")
        disposition = escalate(ACCEPTED_WITH_CONTROLS)

    if not root_radius_admissible(norm["root_radius_mm"], norm["pitch_mm"]):
        findings.append("root-radius-below-the-notch-floor")
        disposition = escalate(REJECTED)

    geometry = {
        "pitch_diameter_mm": pitch_diameter_mm(
            norm["nominal_diameter_mm"], norm["pitch_mm"]
        ),
        "minor_diameter_mm": minor_diameter_mm(
            norm["nominal_diameter_mm"], norm["pitch_mm"]
        ),
        "minimum_root_radius_mm": minimum_root_radius_mm(norm["pitch_mm"]),
    }
    if norm["declared_method"] == ROLLED:
        geometry["rolling_blank_diameter_mm"] = rolling_blank_diameter_mm(
            norm["nominal_diameter_mm"], norm["pitch_mm"]
        )

    allowable = fatigue_allowable_n(
        norm["base_fatigue_allowable_n"],
        norm["declared_method"],
        norm["declared_sequence"],
    )
    duty_met = norm["duty_load_n"] <= allowable + FACTOR_TOLERANCE
    if not duty_met:
        findings.append("duty-load-above-the-fatigue-allowable-earned")
        disposition = escalate(REJECTED)

    return {
        "part_number": norm["part_number"],
        "required_method": required_method,
        "required_sequence": required_sequence,
        "declared_method": norm["declared_method"],
        "declared_sequence": norm["declared_sequence"],
        "geometry": geometry,
        "fatigue_allowable_n": allowable,
        "duty_load_n": norm["duty_load_n"],
        "duty_met": duty_met,
        "controls": controls,
        "findings": findings,
        "disposition": disposition,
    }


def assess_forming_schedule(records):
    """Assess every thread-forming declaration on a build."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    results = []
    seen = set()
    for record in records:
        result = assess_thread_forming(record)
        if result["part_number"] in seen:
            raise ValueError("duplicate part %r" % (result["part_number"],))
        seen.add(result["part_number"])
        results.append(result)
    build = ACCEPTED
    for result in results:
        if _RANK[result["disposition"]] > _RANK[build]:
            build = result["disposition"]
    return {
        "threads": results,
        "build_disposition": build,
        "rejected_parts": [
            r["part_number"] for r in results if r["disposition"] == REJECTED
        ],
        "parts_rolled_after_heat_treatment": [
            r["part_number"]
            for r in results
            if r["declared_sequence"] == ROLL_AFTER_HEAT_TREATMENT
        ],
    }
